"""Quick test for compliance MCP server"""
import sys, json
sys.path.insert(0, r"D:\向海容的知识库\wiki\wiki\记忆宫殿\L5孵化室\产品开发\出海项目\中韩出海数智港\china-korea-digital-port")
from compliance_mcp_server import ComplianceMCPServer, handle_mcp_request

server = ComplianceMCPServer()

# Test 1: initialize
req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
resp = handle_mcp_request(req, server)
print(f"✅ INIT: server={resp['result']['serverInfo']['name']}")

# Test 2: tools/list
req2 = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
resp2 = handle_mcp_request(req2, server)
tools = [t["name"] for t in resp2["result"]["tools"]]
print(f"✅ TOOLS ({len(tools)}): {', '.join(tools)}")

# Test 3: compliance_query
req3 = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "compliance_query", "arguments": {"question": "红参进口需要什么资质"}}}
resp3 = handle_mcp_request(req3, server)
data = json.loads(resp3["result"]["content"][0]["text"])
print(f"✅ QUERY: {data['result_count']} results found for '红参进口需要什么资质'")

# Test 4: compliance_client_health
req4 = {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "compliance_client_health", "arguments": {"client_name": "韩天红参"}}}
resp4 = handle_mcp_request(req4, server)
data4 = json.loads(resp4["result"]["content"][0]["text"])
client_name = list(data4.keys())[0]
score = data4[client_name]["score"]
print(f"✅ HEALTH: {client_name} = {score}/100")

# Test 5: compliance_recent_alerts
req5 = {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "compliance_recent_alerts", "arguments": {"max_level": "high"}}}
resp5 = handle_mcp_request(req5, server)
data5 = json.loads(resp5["result"]["content"][0]["text"])
print(f"✅ ALERTS: {data5['alert_count']} high-level alerts")

# Test 6: compliance_weekly_briefing
req6 = {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "compliance_weekly_briefing", "arguments": {"client_name": "济州海苔", "language": "zh"}}}
resp6 = handle_mcp_request(req6, server)
data6 = json.loads(resp6["result"]["content"][0]["text"])
brief_name = list(data6.keys())[0]
print(f"✅ BRIEFING: {brief_name} - week {data6[brief_name]['week']}")

print("\n🎉 ALL 6 TESTS PASSED")
