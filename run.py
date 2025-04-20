import argparse
import asyncio

def main():
    parser = argparse.ArgumentParser(description="SDRGuardian runner")
    parser.add_argument(
        "--mode",
        choices=["pipeline", "gui"],
        default="pipeline",
        help="Mode to run",
    )
    args = parser.parse_args()
    if args.mode == "pipeline":
        from pipeline import main as pipeline_main
        asyncio.run(pipeline_main())
    else:
        import uvicorn
        uvicorn.run("gui.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()