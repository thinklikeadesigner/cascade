export default function PaymentSuccess() {
  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center px-6">
      <div className="max-w-md w-full text-center">
        <h1 className="text-3xl font-bold mb-4">You&apos;re in.</h1>
        <p className="text-zinc-400 mb-8">
          Payment confirmed. NanoClaw will keep sending your daily tasks.
          Nothing changes on your end — just keep showing up.
        </p>
        <a href="/" className="text-red-400 hover:text-red-300 underline">
          Back to Cascade
        </a>
      </div>
    </div>
  );
}
