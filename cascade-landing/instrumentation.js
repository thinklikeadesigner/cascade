let _spanProcessor;

export async function register() {
  // Only initialize on the server (not edge, not client)
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { NodeSDK } = await import("@opentelemetry/sdk-node");
    const { LangfuseSpanProcessor } = await import("@langfuse/otel");

    _spanProcessor = new LangfuseSpanProcessor();

    const sdk = new NodeSDK({
      spanProcessors: [_spanProcessor],
    });

    sdk.start();
  }
}

export function getLangfuseSpanProcessor() {
  return _spanProcessor;
}
