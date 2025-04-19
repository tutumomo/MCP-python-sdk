"""
MCP UTM 座標轉換伺服器

本伺服器將經緯度與UTM座標互轉功能，包裝為MCP工具，供LLM或MCP客戶端調用。
"""
from mcp.server.fastmcp import FastMCP
from utm_converter import latlon_to_projected, projected_to_latlon

# 建立 MCP 伺服器
mcp = FastMCP("UTM Converter")

@mcp.tool()
def latlon_to_utm(latitude: float, longitude: float, datum: str = "TWD97") -> dict:
    """
    將經緯度轉換為 UTM 座標。
    參數:
        latitude: 緯度 (十進制度)
        longitude: 經度 (十進制度)
        datum: 大地基準 (預設 TWD97)
    回傳:
        dict 包含 easting, northing, zone, hemisphere
    """
    x, y, zone, is_south = latlon_to_projected(latitude, longitude, datum)
    if x is None or y is None:
        raise ValueError("座標轉換失敗，請檢查輸入值。")
    return {
        "easting": x,
        "northing": y,
        "zone": zone,
        "hemisphere": "South" if is_south else "North"
    }

@mcp.tool()
def utm_to_latlon(easting: float, northing: float, zone: int, south: bool = False, datum: str = "TWD97") -> dict:
    """
    將 UTM 座標轉換為經緯度。
    參數:
        easting: UTM X座標
        northing: UTM Y座標
        zone: UTM分帶 (1~60)
        south: 是否為南半球 (預設False)
        datum: 大地基準 (預設 TWD97)
    回傳:
        dict 包含 latitude, longitude
    """
    lon, lat = projected_to_latlon(easting, northing, zone, south, datum)
    if lat is None or lon is None:
        raise ValueError("座標轉換失敗，請檢查輸入值。")
    return {
        "latitude": lat,
        "longitude": lon
    }

# 提供 ASGI 應用給 uvicorn 啟動 HTTP 服務
app = mcp.sse_app()  # 讓 uvicorn 可以直接啟動 HTTP 伺服器

# 若要用 CLI 方式啟動 stdio 服務，仍可保留以下程式
if __name__ == "__main__":
    mcp.run()