import { useState } from "react";

import CalendarTimetable from "../pages/admin/CalendarTimetable";
import HierarchyManager from "../pages/admin/HierarchyManager";
import PromotionTransfer from "../pages/admin/PromotionTransfer";
import StudentImport from "../pages/admin/StudentImport";
import SubjectCatalogue from "../pages/admin/SubjectCatalogue";
import TeacherAssignment from "../pages/admin/TeacherAssignment";

const TABS = [
  { key: "hierarchy", label: "Hierarchy", Component: HierarchyManager },
  { key: "subjects", label: "Subjects", Component: SubjectCatalogue },
  { key: "teachers", label: "Teachers & Owners", Component: TeacherAssignment },
  { key: "students", label: "Student Import", Component: StudentImport },
  { key: "calendar", label: "Calendar & Timetable", Component: CalendarTimetable },
  { key: "promotion", label: "Promotion / Transfer", Component: PromotionTransfer },
] as const;

/**
 * Simple in-memory tab switcher rather than a routing library: Section 5's
 * fixed stack does not name a router, and ADR-0010 deliberately limits
 * supporting-library additions to Vite/python-dotenv/PyJWT. Phase 1's
 * Expected Demo bar does not require deep-linkable URLs, so plain React
 * state is sufficient and avoids introducing an unapproved dependency.
 */
export default function AdminShell() {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]["key"]>("hierarchy");
  const Active = TABS.find((t) => t.key === activeTab)?.Component ?? HierarchyManager;

  return (
    <div>
      <nav className="flex gap-1 border-b bg-white px-4" data-testid="admin-nav">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-2 text-sm ${
              activeTab === tab.key ? "border-b-2 border-blue-600 font-semibold" : "text-gray-600"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      <Active />
    </div>
  );
}
