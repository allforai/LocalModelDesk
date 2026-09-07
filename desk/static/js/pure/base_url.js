// data:gatewayStatus 的 host/port → OpenAI / Anthropic 两条 base URL（R-ui-10）。
const LAN_PLACEHOLDER = "<本机局域网地址>";

export function baseUrls({ host, port, lanHost }) {
  const all = host === "0.0.0.0";
  const displayHost = all ? (lanHost || LAN_PLACEHOLDER) : host;
  let note = null;
  if (all) {
    note = lanHost
      ? `监听所有网卡；其他设备用 ${displayHost} 访问，本机也可用 127.0.0.1`
      : "0.0.0.0 表示监听所有网卡，从其他设备访问请替换为本机局域网 IP";
  }
  return {
    openai: `http://${displayHost}:${port}/v1`,
    anthropic: `http://${displayHost}:${port}`,
    displayHost,
    note,
  };
}
