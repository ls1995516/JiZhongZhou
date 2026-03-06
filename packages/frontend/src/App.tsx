import { useEffect } from "react";
import { Chat } from "./components/Chat";
import { ProjectPanel } from "./components/ProjectPanel";
import { ReferencePanel } from "./components/ReferencePanel";
import { Toolbar } from "./components/Toolbar";
import { Viewer3D } from "./components/Viewer3D";
import { useAppStore } from "./stores/appStore";

export default function App() {
  const showInspector = useAppStore((s) => s.showInspector);
  const showReferences = useAppStore((s) => s.showReferences);
  const refreshProjects = useAppStore((s) => s.refreshProjects);
  const refreshReferences = useAppStore((s) => s.refreshReferences);

  useEffect(() => {
    void refreshProjects();
    void refreshReferences();
  }, [refreshProjects, refreshReferences]);

  return (
    <div className="app">
      <Toolbar />
      <div className="app__body">
        <Chat />
        {showReferences && <ReferencePanel />}
        <Viewer3D />
        {showInspector && <ProjectPanel />}
      </div>
    </div>
  );
}
