import { useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "./store/auth";

export default function App() {
  const bootstrap = useAuth((s) => s.bootstrap);
  const ready = useAuth((s) => s.ready);
  const user = useAuth((s) => s.user);
  const logout = useAuth((s) => s.logout);
  const navigate = useNavigate();

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  if (!ready) {
    return <div className="min-h-screen bg-slate-900 text-slate-100" />;
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-700 px-6 py-3">
        <h1
          className="cursor-pointer text-xl font-bold text-amber-400"
          onClick={() => navigate("/")}
        >
          Deepcards
        </h1>
        {user && (
          <div className="flex items-center gap-4 text-sm">
            <span className="text-slate-300">{user.username}</span>
            <button className="text-slate-400 hover:text-slate-200" onClick={logout}>
              Log out
            </button>
          </div>
        )}
      </header>
      <main className="mx-auto max-w-6xl p-6">
        <Outlet />
      </main>
    </div>
  );
}
