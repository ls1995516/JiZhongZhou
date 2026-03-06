import { useAppStore } from "../stores/appStore";

export function Toolbar() {
  const projectId = useAppStore((s) => s.projectId);
  const projectName = useAppStore((s) => s.project?.metadata.name);
  const savedProjects = useAppStore((s) => s.savedProjects);
  const showInspector = useAppStore((s) => s.showInspector);
  const showReferences = useAppStore((s) => s.showReferences);
  const isSaving = useAppStore((s) => s.isSaving);
  const toggleInspector = useAppStore((s) => s.toggleInspector);
  const toggleReferences = useAppStore((s) => s.toggleReferences);
  const createProject = useAppStore((s) => s.createProject);
  const loadProject = useAppStore((s) => s.loadProject);
  const saveProject = useAppStore((s) => s.saveProject);

  const handleNew = () => {
    const name = window.prompt("Project name:", "My Building");
    if (name) void createProject(name);
  };

  const handleLoad = (nextProjectId: string) => {
    if (!nextProjectId || nextProjectId === projectId) return;
    void loadProject(nextProjectId);
  };

  return (
    <div className="toolbar">
      <span className="toolbar__title">Building Studio</span>
      {projectId && (
        <span className="toolbar__project">{projectName ?? projectId}</span>
      )}
      <div className="toolbar__actions">
        <button onClick={handleNew}>New Project</button>
        <button onClick={() => void saveProject()} disabled={!projectId || isSaving}>
          {isSaving ? "Saving..." : "Save"}
        </button>
        <select
          aria-label="Load saved project"
          className="toolbar__select"
          onChange={(e) => handleLoad(e.target.value)}
          value={projectId ?? ""}
        >
          <option value="">Load Project</option>
          {savedProjects.map((project) => (
            <option key={project.project_id} value={project.project_id}>
              {project.name}
            </option>
          ))}
        </select>
        <button onClick={toggleInspector}>
          {showInspector ? "Hide" : "Show"} Inspector
        </button>
        <button onClick={toggleReferences}>
          {showReferences ? "Hide" : "Show"} References
        </button>
      </div>
    </div>
  );
}
