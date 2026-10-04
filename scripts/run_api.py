import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Start the SupplyChainLens FastAPI Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable live code reloading")
    parser.add_argument("--backend", default=None, help="Default graph backend ('igraph' or 'networkx')")

    args = parser.parse_args()

    if args.backend:
        import os
        os.environ["GRAPH_BACKEND"] = args.backend

    print(f"Starting SupplyChainLens API server on http://{args.host}:{args.port}")
    print(f"Interactive OpenAPI Documentation: http://{args.host}:{args.port}/docs")
    uvicorn.run("supplychainlens.api:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
