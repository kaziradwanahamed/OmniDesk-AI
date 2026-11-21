export function StreamingIndicator() {
  return (
    <div
      className="flex items-center gap-1 py-5"
      role="status"
      aria-label="Assistant is responding"
    >
      <span className="h-2 w-2 animate-bounce rounded-full bg-tertiary [animation-delay:-0.3s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-tertiary [animation-delay:-0.15s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-tertiary" />
    </div>
  );
}
