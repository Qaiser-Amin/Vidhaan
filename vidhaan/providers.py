"""Only a configured Ollama HTTP endpoint. No automatic model pull or paid API."""
import json
import threading
import time
from urllib.parse import urlsplit
import httpx
from .models import GeneratedAnswer

GENERATION_LOCK = threading.Lock()


class ProviderError(RuntimeError):
    pass


class Ollama:
    def __init__(self, settings, client=None):
        self.settings = settings
        parts = urlsplit(settings.ollama_url)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            raise ValueError('Ollama needs a valid local HTTP(S) server URL')
        self.own_client = client is None
        self.client = client or httpx.Client(base_url=settings.ollama_url.rstrip('/'),
            timeout=httpx.Timeout(settings.timeout_seconds, connect=3), trust_env=False)

    def close(self):
        if self.own_client:
            self.client.close()

    def status(self):
        try:
            response = self.client.get('/api/tags', timeout=3)
            response.raise_for_status()
            data = response.json()
            names = [str(m.get('name', m.get('model', ''))) for m in data.get('models', [])]
            return {'available': True, 'model_available': self.settings.model in names if self.settings.model else False,
                    'models': names, 'message': 'Local Ollama responds'}
        except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
            return {'available': False, 'model_available': False, 'models': [],
                    'message': f'Ollama unavailable ({type(exc).__name__}). Start Ollama locally; evidence-only search works.'}

    def generate(self, prompt, stream=True, on_progress=None):
        status = self.status()
        if not status['available']:
            raise ProviderError(status['message'])
        if not status['model_available']:
            raise ProviderError(f'Model {self.settings.model!r} is not installed. Run ollama pull with the chosen candidate, or use evidence_only.')
        payload = {'model': self.settings.model, 'prompt': prompt, 'stream': stream, 'think': False,
                   'format': GeneratedAnswer.model_json_schema(), 'options': {'temperature': 0,
                   'num_ctx': self.settings.context_tokens, 'num_predict': self.settings.output_tokens}}
        start = time.perf_counter()
        if not GENERATION_LOCK.acquire(timeout=1):
            raise ProviderError('One generation is already running; wait before another request')
        try:
            text = ''
            final = {}
            if stream:
                try:
                    with self.client.stream('POST', '/api/generate', json=payload) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if time.perf_counter()-start > self.settings.timeout_seconds:
                                raise ProviderError('Generation exceeded total wall-time timeout')
                            if not line:
                                continue
                            item = json.loads(line)
                            if item.get('error'):
                                raise ProviderError(str(item['error'])[:300])
                            text += item.get('response', '')
                            if len(text) > 50_000:
                                raise ProviderError('Generated response exceeds the bounded output limit')
                            if on_progress:
                                on_progress(len(text))  # Unvalidated text is never shown as an answer.
                            if item.get('done'):
                                final = item
                                break
                    if not final:
                        raise ProviderError('Incomplete Ollama stream')
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code not in (400, 405, 501):
                        raise
                    # A bounded fallback for endpoints without streaming/schema support.
                    payload['stream'] = False
                    response = self.client.post('/api/generate', json=payload)
                    response.raise_for_status()
                    final = response.json()
                    text = final.get('response', '')
            else:
                response = self.client.post('/api/generate', json=payload)
                response.raise_for_status()
                final = response.json()
                text = final.get('response', '')
            if not isinstance(text, str) or len(text) > 50_000:
                raise ProviderError('Malformed or oversized Ollama response')
            answer = GeneratedAnswer.model_validate_json(text)
            metrics = {key:final.get(key) for key in ('prompt_eval_count','eval_count','eval_duration','total_duration')}
            duration = final.get('eval_duration')
            metrics['tokens_per_second'] = (final['eval_count'] / (duration / 1e9)) if duration and final.get('eval_count') else None
            metrics['generation_wall_seconds'] = time.perf_counter()-start
            return answer, metrics
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            raise ProviderError(f'Local generation failed ({type(exc).__name__}); use the displayed extracts.') from exc
        finally:
            GENERATION_LOCK.release()
