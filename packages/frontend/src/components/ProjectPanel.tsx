import { useAppStore } from "../stores/appStore";

export function ProjectPanel() {
  const project = useAppStore((s) => s.project);
  const scene = useAppStore((s) => s.scene);
  const showInspector = useAppStore((s) => s.showInspector);

  if (!showInspector) return null;

  return (
    <div className="inspector-panel">
      <h3>Project JSON</h3>
      <pre className="inspector-json">
        {project ? JSON.stringify(project, null, 2) : "No project loaded"}
      </pre>

      <h3>Scene JSON</h3>
      <pre className="inspector-json">
        {scene ? JSON.stringify(scene, null, 2) : "No scene compiled"}
      </pre>
    </div>
  );
}
