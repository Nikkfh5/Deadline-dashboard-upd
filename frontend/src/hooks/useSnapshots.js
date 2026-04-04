import { useState, useEffect } from 'react';

const STORAGE_KEY = 'deadline-snapshots';

export function useSnapshots() {
  const [snapshots, setSnapshots] = useState([]);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      setSnapshots(JSON.parse(saved));
    }
  }, []);

  const persist = (next) => {
    setSnapshots(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  };

  const saveSnapshot = (name, deadlines) => {
    const snapshot = {
      id: Date.now().toString(),
      name: name.trim() || `Snapshot ${new Date().toLocaleDateString()}`,
      createdAt: new Date().toISOString(),
      deadlines: deadlines.map((d) => ({
        id: d.id,
        name: d.name,
        task: d.task,
        dueDate: d.dueDate,
        daysNeeded: d.daysNeeded,
      })),
    };
    const next = [snapshot, ...snapshots];
    persist(next);
    return snapshot;
  };

  const deleteSnapshot = (id) => {
    persist(snapshots.filter((s) => s.id !== id));
  };

  const exportSnapshotAsText = (snapshot) => {
    const lines = [`Snapshot: "${snapshot.name}" (${new Date(snapshot.createdAt).toLocaleDateString()})`];
    snapshot.deadlines.forEach((d) => {
      if (d.daysNeeded) {
        lines.push(`  - ${d.name}: ${d.daysNeeded} days needed (due ${new Date(d.dueDate).toLocaleDateString()})`);
      }
    });
    return lines.join('\n');
  };

  return { snapshots, saveSnapshot, deleteSnapshot, exportSnapshotAsText };
}
