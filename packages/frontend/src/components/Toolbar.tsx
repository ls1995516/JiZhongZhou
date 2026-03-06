import { useAppStore } from "../stores/appStore";

export function Toolbar() {
  const projectId = useAppStore((s) => s.projectId);
  const projectName = useAppStore((s) => s.project?.metadata.name);
  const showInspector = useAppStore((s) => s.showInspector);
  const toggleInspector = useAppStore((s) => s.toggleInspector);
  const createProject = useAppStore((s) => s.createProject);

  const handleNew = () => {
    const name = window.prompt("Project name:", "My Building");
    if (name) createProject(name);
  };

  return (
    <div className="toolbar">
      <span className="toolbar__title">Building Studio</span>
      {projectId && (
        <span className="toolbar__project">{projectName ?? projectId}</span>
      )}
      <div className="toolbar__actions">
        <button onClick={handleNew}>New Project</button>
        <button onClick={toggleInspector}>
          {showInspector ? "Hide" : "Show"} Inspector
        </button>
      </div>
    </div>
  );
}
