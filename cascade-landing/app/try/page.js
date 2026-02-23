import CascadeDemoWidget from "@/components/CascadeDemoWidget";

export const metadata = {
  title: "Try Cascade | Break any goal into today's action",
  description:
    "Tell Cascade your goal and watch it break down into an actionable execution plan. Free demo — no signup required.",
};

export default function TryPage() {
  return (
    <div className="try-page">
      <CascadeDemoWidget fullScreen />
    </div>
  );
}
