from fastmcp import FastMCP
import random 
mcp = FastMCP("Remote-MCPServer")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers. if not given then it will randomly generate t  hem"""
    if a is None:
        a = random.randint(1, 100)
    if b is None:
        b = random.randint(1, 100)
    return a + b

if __name__ == "__main__":
    mcp.run(transport = "http",host = "0.0.0.0",port = 8000)