import { useAppStore } from "../stores/appStore";

export function ReferencePanel() {
  const references = useAppStore((s) => s.references);
  const loadReference = useAppStore((s) => s.loadReference);

  return (
    <aside className="reference-panel">
      <h3>References</h3>
      {references.length === 0 ? (
        <p className="reference-panel__empty">No references available.</p>
      ) : (
        <div className="reference-panel__list">
          {references.map((reference) => (
            <div key={reference.id} className="reference-card">
              <div className="reference-card__header">
                <strong>{reference.title}</strong>
                <span>{reference.version}</span>
              </div>
              <p className="reference-card__description">{reference.description}</p>
              <p className="reference-card__tags">{reference.tags.join(", ")}</p>
              <button onClick={() => void loadReference(reference.id)}>
                Load Into Workspace
              </button>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
