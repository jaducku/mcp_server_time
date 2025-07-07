"""
AWS Lambda용 MCP Time Server (FastMCP + streamable HTTP + Mangum)
- Lambda Handler로 바로 쓸 수 있음
- FastAPI 앱 추출하여 handler로 연결
"""

from fastmcp import MCPServer, mcp_tool, mcp_arg
from datetime import datetime, time as dt_time
import pytz
import zoneinfo
import os
from mangum import Mangum

def get_local_timezone():
    try:
        return zoneinfo.ZoneInfo(os.environ.get("TZ", "UTC"))
    except Exception:
        try:
            import tzlocal
            return pytz.timezone(tzlocal.get_localzone_name())
        except Exception:
            return pytz.UTC

local_timezone = get_local_timezone()

@mcp_tool(
    name="get_current_time",
    description="지정된 IANA 타임존에 대한 현재 시각을 ISO8601 형식으로 반환."
)
@mcp_arg("timezone", str, description="IANA 타임존 문자열, 예시: 'Asia/Seoul', 'Europe/Warsaw'. 비워두면 서버 기본 타임존.")
def get_current_time(timezone: str = None):
    tz = None
    if timezone:
        try:
            tz = zoneinfo.ZoneInfo(timezone)
        except Exception:
            try:
                tz = pytz.timezone(timezone)
            except Exception:
                tz = local_timezone
    else:
        tz = local_timezone
    now = datetime.now(tz)
    return {
        "timezone": str(tz),
        "iso8601": now.isoformat(),
        "dst": bool(getattr(now, 'dst', lambda: False)()),
        "utc_offset_hours": now.utcoffset().total_seconds() / 3600 if now.utcoffset() else 0
    }

@mcp_tool(
    name="convert_time",
    description="주어진 HH:MM 시각을 source 타임존에서 target 타임존으로 변환하여 ISO8601로 반환"
)
@mcp_arg("source_timezone", str, description="변환 전 IANA 타임존")
@mcp_arg("time", str, description="시각 (HH:MM)")
@mcp_arg("target_timezone", str, description="변환 후 IANA 타임존")
def convert_time(source_timezone: str, time: str, target_timezone: str):
    try:
        src_tz = zoneinfo.ZoneInfo(source_timezone)
    except Exception:
        src_tz = pytz.timezone(source_timezone)
    try:
        tgt_tz = zoneinfo.ZoneInfo(target_timezone)
    except Exception:
        tgt_tz = pytz.timezone(target_timezone)
    dt_naive = datetime.combine(datetime.now().date(), dt_time.fromisoformat(time))
    dt_src = dt_naive.replace(tzinfo=src_tz)
    dt_tgt = dt_src.astimezone(tgt_tz)
    return {
        "source_time": dt_src.isoformat(),
        "source_timezone": str(src_tz),
        "target_time": dt_tgt.isoformat(),
        "target_timezone": str(tgt_tz),
        "dst_source": bool(getattr(dt_src, 'dst', lambda: False)()),
        "dst_target": bool(getattr(dt_tgt, 'dst', lambda: False)()),
        "utc_offset_diff_hours": (
            (dt_tgt.utcoffset().total_seconds() - dt_src.utcoffset().total_seconds()) / 3600
        ) if dt_tgt.utcoffset() and dt_src.utcoffset() else None
    }

# Lambda용 FastAPI/MCP서버 app 및 handler
server = MCPServer(
    title="Time MCP Server (Lambda)",
    description="AWS Lambda에서 동작하는 MCP 서버 (FastMCP, streamable-http)",
    version="1.0.0",
    streamable_http=True
)
app = server.app
handler = Mangum(app)
