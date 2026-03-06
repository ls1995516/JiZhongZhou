import { useEffect } from "react";
import { Chat } from "./components/Chat";
import { ProjectPanel } from "./components/ProjectPanel";
import { Toolbar } from "./components/Toolbar";
import { Viewer3D } from "./components/Viewer3D";
import { useAppStore } from "./stores/appStore";

export default function App() {
  const showInspector = useAppStore((s) => s.showInspector);
  const refreshProjects = useAppStore((s) => s.refreshProjects);

  useEffect(() => {
    void refreshProjects();
  }, [refreshProjects]);

  return (
    <div className="app">
      <Toolbar />
      <div className="app__body">
        <Chat />
        <Viewer3D />
        {showInspector && <ProjectPanel />}
      </div>
    </div>
  );
}
