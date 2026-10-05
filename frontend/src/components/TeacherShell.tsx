import { useState } from "react";

import { useMySubjects } from "../api/contentApi";
import CurriculumPage from "../pages/teacher/CurriculumPage";
import SubjectContent from "../pages/teacher/SubjectContent";
import TeacherSubjects from "../pages/teacher/TeacherSubjects";

type Tab = "content" | "curriculum";

/** Teacher area (Phase 2): subject picker with Content (2A) and Curriculum (2B) tabs.
 * Plain state, no router (ADR-0010 keeps the dependency list closed). */
export default function TeacherShell() {
  const { data } = useMySubjects();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("content");
  const selected = (data ?? []).find((s) => s.id === selectedId) ?? null;
  return (
    <div data-testid="teacher-shell">
      <TeacherSubjects selectedId={selectedId} onSelect={setSelectedId} />
      {selected && (
        <>
          <div role="tablist" className="flex gap-2 px-4">
            <button role="tab" aria-selected={tab === "content"} onClick={() => setTab("content")}>
              Content
            </button>
            <button
              role="tab"
              aria-selected={tab === "curriculum"}
              onClick={() => setTab("curriculum")}
            >
              Curriculum
            </button>
          </div>
          {tab === "content" ? (
            <SubjectContent subject={selected} />
          ) : (
            <CurriculumPage subject={selected} />
          )}
        </>
      )}
    </div>
  );
}
