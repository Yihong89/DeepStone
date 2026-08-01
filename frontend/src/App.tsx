import { Outlet } from "react-router-dom";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <header className="border-b border-slate-700 px-6 py-3">
        <h1 className="text-xl font-bold text-amber-400">Deepcards</h1>
      </header>
      <main className="mx-auto max-w-6xl p-6">
        <Outlet />
      </main>
    </div>
  );
}
