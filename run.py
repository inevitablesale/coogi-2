#!/usr/bin/env python3

import uvicorn
from api import app

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port) 