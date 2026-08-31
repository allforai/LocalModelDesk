// data:gatewayStatus 的 host/port → OpenAI / Anthropic 两条 base URL（R-ui-10）。
const LAN_PLACEHOLDER = "<本机局域网地址>";

export function baseUrls({ host, port }) {
  const all = host === "0.0.0.0";
  const displayHost = all ? LAN_PLACEHOLDER : host;
  return {
    openai: `http://${displayHost}:${port}/v1`,
    anthropic: `http://${displayHost}:${port}`,
    displayHost,
    note: all ? "0.0.0.0 表示监听所有网卡，从其他设备访问请替换为本机局域网 IP" : null,
  };
}
