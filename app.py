"""Local VIDHAAN web server. The compiled React interface ships with the project."""
import argparse
import os
from vidhaan.webapp import create_app

app = create_app()

if __name__ == '__main__':
    import uvicorn
    parser = argparse.ArgumentParser(description='Start the local VIDHAAN workspace')
    parser.add_argument('--port', type=int, default=int(os.getenv('VIDHAAN_PORT', '8765')))
    args = parser.parse_args()
    uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False)
