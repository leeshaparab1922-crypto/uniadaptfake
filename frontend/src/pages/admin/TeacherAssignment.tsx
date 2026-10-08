import React, { useState, useEffect, type FormEvent } from "react";

type CourseComponent = "THEORY" | "PRACTICAL" | "TUTORIAL";

interface TeacherItem {
  id: string;
  name: string;
  email: string;
  departmentCode: string;
}

interface AssignmentItem {
  id: string;
  teacherId: string;
  teacherName: string;
  teacherEmail: string;
  departmentCode: string;
  subjectCode: string;
  subjectName: string;
  component: CourseComponent;
  role: "PRIMARY" | "CO-PRIMARY";
}

interface ToastAlert {
  text: string;
  type: "success" | "warning" | "error";
}

export default function TeachersAndOwners() {
  const activeInstName = localStorage.getItem("uniadapt_active_institute_name") || "finolex";

  // 1. Departments dynamically loaded from Hierarchy Master Storage
  const [departments, setDepartments] = useState<{ code: string; name: string }[]>(() => {
    const master = localStorage.getItem("uniadapt_master_departments");
    if (master) {
      try {
        const parsed = JSON.parse(master);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      } catch (e) {
        console.error(e);
      }
    }
    const customNames = localStorage.getItem("uniadapt_edited_depts");
    if (customNames) {
      try {
        const parsed = JSON.parse(customNames);
        const list = Object.values(parsed) as { code: string; name: string }[];
        if (list.length > 0) return list;
      } catch (e) {
        console.error(e);
      }
    }
    return [
      { code: "CSE2024", name: "Computer Science" },
      { code: "CSE2005", name: "Computer Science Engineering" },
      { code: "CSL102", name: "cse" },
      { code: "IT2004", name: "Information Technology" },
    ];
  });

  useEffect(() => {
    const handleSync = () => {
      const master = localStorage.getItem("uniadapt_master_departments");
      if (master) {
        try {
          const parsed = JSON.parse(master);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setDepartments(parsed);
          }
        } catch (e) {
          console.error(e);
        }
      }
    };
    handleSync();
    window.addEventListener("storage", handleSync);
    return () => window.removeEventListener("storage", handleSync);
  }, []);

  // 2. Subjects catalogue loaded from storage
  const [catalogueSubjects] = useState<{ code: string; name: string; departmentCode: string; component: CourseComponent }[]>(() => {
    const cached = localStorage.getItem("uniadapt_subject_catalogue");
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        return parsed.map((s: any) => ({
          code: s.code,
          name: s.name,
          departmentCode: s.departmentCode,
          component: (s.component as CourseComponent) || "THEORY",
        }));
      } catch (e) {
        console.error(e);
      }
    }
    return [
      { code: "CG2008", name: "Computer Graphics", departmentCode: "CSE2024", component: "THEORY" },
      { code: "MATH2005", name: "Engineering Mathematics 1", departmentCode: "IT2004", component: "THEORY" },
      { code: "BEE2005", name: "BEE", departmentCode: "IT2004", component: "PRACTICAL" },
      { code: "CS102", name: "Data Structures & Algorithms", departmentCode: "CSE2024", component: "THEORY" },
    ];
  });

  const [activeTab, setActiveTab] = useState<"assign" | "teachers_list">("assign");
  const [selectedDeptFilter, setSelectedDeptFilter] = useState<string>("ALL");

  // Form 1: Add Teacher
  const [teacherName, setTeacherName] = useState("");
  const [teacherEmail, setTeacherEmail] = useState("");
  const [teacherDept, setTeacherDept] = useState(departments[0]?.code || "CSE2024");

  // Form 2: Assign Teacher
  const [assignDept, setAssignDept] = useState(departments[0]?.code || "CSE2024");
  const [selectedTeacherId, setSelectedTeacherId] = useState("");
  const [selectedSubjectCode, setSelectedSubjectCode] = useState("");
  const [assignedRole, setAssignedRole] = useState<"PRIMARY" | "CO-PRIMARY">("PRIMARY");

  // Toast State
  const [toast, setToast] = useState<ToastAlert | null>(null);

  // Storage: Teachers List
  const [teachersList, setTeachersList] = useState<TeacherItem[]>(() => {
    const cached = localStorage.getItem("uniadapt_teachers_list");
    return cached
      ? JSON.parse(cached)
      : [
          {
            id: "tch-1",
            name: "Prof. Sanika Parab",
            email: "sanika.parab@finolex.edu",
            departmentCode: "CSE2024",
          },
          {
            id: "tch-2",
            name: "Dipti Morajkar",
            email: "diptimorajkar@gmail.com",
            departmentCode: "IT2004",
          },
        ];
  });

  // Storage: Assignments
  const [assignments, setAssignments] = useState<AssignmentItem[]>(() => {
    const cached = localStorage.getItem("uniadapt_teacher_assignments");
    return cached
      ? JSON.parse(cached)
      : [
          {
            id: "asg-1",
            teacherId: "tch-1",
            teacherName: "Prof. Sanika Parab",
            teacherEmail: "sanika.parab@finolex.edu",
            departmentCode: "CSE2024",
            subjectCode: "CG2008",
            subjectName: "Computer Graphics",
            component: "THEORY",
            role: "PRIMARY",
          },
        ];
  });

  const [editingAssignment, setEditingAssignment] = useState<AssignmentItem | null>(null);
  const [editingTeacher, setEditingTeacher] = useState<TeacherItem | null>(null);

  useEffect(() => {
    localStorage.setItem("uniadapt_teachers_list", JSON.stringify(teachersList));
  }, [teachersList]);

  useEffect(() => {
    localStorage.setItem("uniadapt_teacher_assignments", JSON.stringify(assignments));
  }, [assignments]);

  const deptTeachers = teachersList.filter((t) => t.departmentCode === assignDept);
  const deptSubjects = catalogueSubjects.filter((s) => s.departmentCode === assignDept);

  const handleDepartmentChange = (newDept: string) => {
    setAssignDept(newDept);
    const validTeachers = teachersList.filter((t) => t.departmentCode === newDept);
    const validSubjects = catalogueSubjects.filter((s) => s.departmentCode === newDept);
    setSelectedTeacherId(validTeachers.length > 0 ? validTeachers[0].id : "");
    setSelectedSubjectCode(validSubjects.length > 0 ? validSubjects[0].code : "");
  };

  const triggerToast = (text: string, type: "success" | "warning" | "error" = "success") => {
    setToast({ text, type });
    setTimeout(() => {
      setToast(null);
    }, 4000);
  };

  const getComponentDisplay = (comp: CourseComponent) => {
    if (comp === "PRACTICAL") return "Practical / Lab (PR)";
    if (comp === "TUTORIAL") return "Tutorial (TUT)";
    return "Theory (TH)";
  };

  const renderComponentBadge = (comp: CourseComponent) => {
    if (comp === "PRACTICAL") {
      return (
        <span className="bg-cyan-50 text-cyan-800 border border-cyan-200 font-extrabold text-[10px] px-2.5 py-0.5 rounded-full inline-flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" /> Practical / Lab
        </span>
      );
    }
    if (comp === "TUTORIAL") {
      return (
        <span className="bg-amber-50 text-amber-800 border border-amber-200 font-extrabold text-[10px] px-2.5 py-0.5 rounded-full inline-flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> Tutorial
        </span>
      );
    }
    return (
      <span className="bg-indigo-50 text-indigo-700 border border-indigo-200 font-extrabold text-[10px] px-2.5 py-0.5 rounded-full inline-flex items-center gap-1">
        <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" /> Theory
      </span>
    );
  };

  const handleAddTeacher = (e: FormEvent) => {
    e.preventDefault();
    if (!teacherName.trim() || !teacherEmail.trim()) {
      triggerToast("Please provide valid teacher name and email address.", "warning");
      return;
    }

    const cleanEmail = teacherEmail.trim().toLowerCase();
    if (teachersList.some((t) => t.email.toLowerCase() === cleanEmail)) {
      triggerToast(`Teacher with email "${cleanEmail}" already exists!`, "error");
      return;
    }

    const newTeacher: TeacherItem = {
      id: "tch-" + Date.now(),
      name: teacherName.trim(),
      email: cleanEmail,
      departmentCode: teacherDept,
    };

    setTeachersList((prev) => [...prev, newTeacher]);
    setAssignDept(teacherDept);
    setSelectedTeacherId(newTeacher.id);

    triggerToast(`Teacher "${newTeacher.name}" registered successfully!`, "success");
    setTeacherName("");
    setTeacherEmail("");
  };

  const handleAssignTeacher = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const formTeacherId = String(formData.get("teacherId") || "").trim();
    const formSubjectCode = String(formData.get("subjectCode") || "").trim();
    const formRole = String(formData.get("role") || "PRIMARY") as "PRIMARY" | "CO-PRIMARY";

    if (!formTeacherId) {
      triggerToast("Please select a teacher from the dropdown.", "warning");
      return;
    }
    if (!formSubjectCode) {
      triggerToast("Please select a subject from the dropdown.", "warning");
      return;
    }

    const teacherObj = teachersList.find((t) => t.id === formTeacherId);
    if (!teacherObj) {
      triggerToast("Selected teacher not found.", "error");
      return;
    }

    const subjectObj =
      catalogueSubjects.find((s) => s.code === formSubjectCode && s.departmentCode === assignDept) ||
      catalogueSubjects.find((s) => s.code === formSubjectCode);

    if (!subjectObj) {
      triggerToast("Selected subject not found.", "error");
      return;
    }

    const alreadyAssigned = assignments.some(
      (a) => a.teacherId === teacherObj.id && a.subjectCode === subjectObj.code
    );
    if (alreadyAssigned) {
      triggerToast(`Teacher "${teacherObj.name}" is already assigned to ${subjectObj.code}!`, "warning");
      return;
    }

    const newAssignment: AssignmentItem = {
      id: "asg-" + Date.now(),
      teacherId: teacherObj.id,
      teacherName: teacherObj.name,
      teacherEmail: teacherObj.email,
      departmentCode: assignDept,
      subjectCode: subjectObj.code,
      subjectName: subjectObj.name,
      component: subjectObj.component || "THEORY",
      role: formRole,
    };

    setAssignments((prev) => [newAssignment, ...prev]);
    setSelectedDeptFilter(assignDept);

    triggerToast(
      `Assigned ${teacherObj.name} to "${subjectObj.code} - ${subjectObj.name} (${getComponentDisplay(newAssignment.component)})" as ${formRole}!`,
      "success"
    );
  };

  const handleDeleteAssignment = (id: string, tName: string, sCode: string) => {
    if (window.confirm(`Unassign ${tName} from subject ${sCode}?`)) {
      setAssignments((prev) => prev.filter((a) => a.id !== id));
      triggerToast(`Assignment for ${tName} removed.`, "success");
    }
  };

  const handleDeleteTeacher = (id: string, name: string) => {
    if (window.confirm(`Delete teacher "${name}" and remove their course assignments?`)) {
      setTeachersList((prev) => prev.filter((t) => t.id !== id));
      setAssignments((prev) => prev.filter((a) => a.teacherId !== id));
      triggerToast(`Teacher "${name}" deleted.`, "success");
    }
  };

  const handleSaveAssignmentComprehensiveEdit = (e: FormEvent) => {
    e.preventDefault();
    if (!editingAssignment) return;

    setTeachersList((prev) =>
      prev.map((t) =>
        t.id === editingAssignment.teacherId
          ? {
              ...t,
              name: editingAssignment.teacherName.trim(),
              email: editingAssignment.teacherEmail.trim().toLowerCase(),
              departmentCode: editingAssignment.departmentCode,
            }
          : t
      )
    );

    setAssignments((prev) =>
      prev.map((a) => (a.id === editingAssignment.id ? { ...editingAssignment } : a))
    );

    triggerToast(`Assignment details for "${editingAssignment.teacherName}" updated!`, "success");
    setEditingAssignment(null);
  };

  const handleSaveTeacherComprehensiveEdit = (e: FormEvent) => {
    e.preventDefault();
    if (!editingTeacher) return;

    setTeachersList((prev) =>
      prev.map((t) => (t.id === editingTeacher.id ? { ...editingTeacher } : t))
    );

    setAssignments((prev) =>
      prev.map((a) =>
        a.teacherId === editingTeacher.id
          ? {
              ...a,
              teacherName: editingTeacher.name.trim(),
              teacherEmail: editingTeacher.email.trim().toLowerCase(),
              departmentCode: editingTeacher.departmentCode,
            }
          : a
      )
    );

    triggerToast(`Teacher profile for "${editingTeacher.name}" updated!`, "success");
    setEditingTeacher(null);
  };

  const filteredAssignments =
    selectedDeptFilter === "ALL"
      ? assignments
      : assignments.filter((a) => a.departmentCode === selectedDeptFilter);

  const filteredTeachers =
    selectedDeptFilter === "ALL"
      ? teachersList
      : teachersList.filter((t) => t.departmentCode === selectedDeptFilter);

  return (
    <div className="min-h-screen bg-[#eaf4fe] p-4 sm:p-6 lg:p-8 space-y-6 font-sans text-slate-800">
      {toast && (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50 animate-bounce">
          <div
            className={`flex items-center gap-3 px-6 py-3.5 rounded-2xl shadow-2xl border text-sm font-extrabold text-white ${
              toast.type === "success"
                ? "bg-gradient-to-r from-emerald-600 to-teal-700 border-emerald-300 shadow-emerald-950/30"
                : toast.type === "warning"
                ? "bg-gradient-to-r from-amber-600 to-orange-700 border-amber-300 shadow-orange-950/30"
                : "bg-gradient-to-r from-rose-600 to-red-700 border-rose-300 shadow-rose-950/30"
            }`}
          >
            <span className="text-xl">
              {toast.type === "success" ? "✅" : toast.type === "warning" ? "⚠️" : "🚫"}
            </span>
            <span>{toast.text}</span>
            <button
              onClick={() => setToast(null)}
              className="ml-3 bg-white/20 hover:bg-white/30 rounded-full w-5 h-5 flex items-center justify-center text-xs"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* HERO BANNER */}
      <div className="relative overflow-hidden rounded-[24px] bg-gradient-to-r from-[#07193b] via-[#09295e] to-[#04122d] border border-cyan-400/40 p-6 sm:p-7 shadow-xl shadow-blue-950/20">
        <div className="absolute -top-16 -right-16 w-80 h-80 bg-cyan-400/20 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="bg-[#0e3b79] text-cyan-300 border border-cyan-400/40 text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                FACULTY & LAB ASSIGNMENT
              </span>
              <span className="text-cyan-300 text-xs font-bold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                {activeInstName}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
              Teacher & Subject Owner Assignment
            </h1>
            <p className="text-xs sm:text-sm text-cyan-100/80 mt-0.5">
              Allocate Theory lectures and Practical/Lab sessions with Primary and Co-Primary roles.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-[#05142f]/85 p-1.5 rounded-2xl border border-cyan-500/30 shadow-inner backdrop-blur-md">
            <button
              type="button"
              onClick={() => setActiveTab("assign")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
                activeTab === "assign"
                  ? "bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white shadow-lg shadow-cyan-500/30 ring-1 ring-cyan-300/60"
                  : "text-cyan-100/70 hover:text-white"
              }`}
            >
              📋 Assigned Teachers & Subjects ({assignments.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("teachers_list")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
                activeTab === "teachers_list"
                  ? "bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white shadow-lg shadow-cyan-500/30 ring-1 ring-cyan-300/60"
                  : "text-cyan-100/70 hover:text-white"
              }`}
            >
              👥 Teachers Directory ({teachersList.length})
            </button>
          </div>
        </div>
      </div>

      {/* FORMS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ADD TEACHER */}
        <div className="bg-white rounded-2xl p-6 border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] space-y-4">
          <div className="flex items-center gap-3 border-b border-cyan-50 pb-3">
            <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200 text-blue-700 font-black flex items-center justify-center text-lg">
              👨‍🏫
            </div>
            <div>
              <h3 className="font-extrabold text-slate-900 text-sm">Add New Teacher</h3>
              <p className="text-[11px] text-slate-500">Register faculty under a specific department</p>
            </div>
          </div>

          <form onSubmit={handleAddTeacher} className="space-y-3.5">
            <div>
              <label className="text-[11px] font-bold text-slate-600 uppercase">Teacher Full Name *</label>
              <input
                type="text"
                placeholder="e.g. Dipti Morajkar"
                value={teacherName}
                onChange={(e) => setTeacherName(e.target.value)}
                required
                className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-semibold text-slate-900 outline-none focus:ring-2 focus:ring-cyan-400"
              />
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-600 uppercase">Teacher Email Address *</label>
              <input
                type="email"
                placeholder="e.g. diptimorajkar@gmail.com"
                value={teacherEmail}
                onChange={(e) => setTeacherEmail(e.target.value)}
                required
                className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-semibold text-slate-900 outline-none focus:ring-2 focus:ring-cyan-400"
              />
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-600 uppercase">Assign to Department *</label>
              <select
                value={teacherDept}
                onChange={(e) => setTeacherDept(e.target.value)}
                className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 bg-[#f7fbff] outline-none focus:ring-2 focus:ring-cyan-400"
              >
                {departments.map((d) => (
                  <option key={d.code} value={d.code}>
                    {d.name} ({d.code})
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              className="w-full bg-gradient-to-r from-[#1d63ea] to-[#0295e6] hover:from-[#1554cd] hover:to-[#0284cc] text-white font-bold py-2.5 rounded-xl text-xs transition shadow-md shadow-blue-500/25 flex items-center justify-center gap-1.5"
            >
              + Register Teacher
            </button>
          </form>
        </div>

        {/* ASSIGN TEACHER */}
        <div className="bg-white rounded-2xl p-6 border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] space-y-4">
          <div className="flex items-center gap-3 border-b border-cyan-50 pb-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-50 border border-cyan-200 text-cyan-700 font-black flex items-center justify-center text-lg">
              📚
            </div>
            <div>
              <h3 className="font-extrabold text-slate-900 text-sm">Assign Teacher to Subject</h3>
              <p className="text-[11px] text-slate-500">Allocate Theory/Lab course with ownership role</p>
            </div>
          </div>

          <form onSubmit={handleAssignTeacher} className="space-y-3.5">
            <div>
              <label className="text-[11px] font-bold text-slate-600 uppercase">Department *</label>
              <select
                name="departmentCode"
                value={assignDept}
                onChange={(e) => handleDepartmentChange(e.target.value)}
                className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 bg-[#f7fbff] outline-none focus:ring-2 focus:ring-cyan-400"
              >
                {departments.map((d) => (
                  <option key={d.code} value={d.code}>
                    {d.name} ({d.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-600 uppercase">Select Teacher *</label>
              <select
                name="teacherId"
                value={selectedTeacherId || (deptTeachers.length > 0 ? deptTeachers[0].id : "")}
                onChange={(e) => setSelectedTeacherId(e.target.value)}
                required
                className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 bg-white outline-none focus:ring-2 focus:ring-cyan-400"
              >
                {deptTeachers.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.email})
                  </option>
                ))}
                {deptTeachers.length === 0 && <option value="">No teachers available in this department</option>}
              </select>
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-600 uppercase">Select Subject *</label>
              <select
                name="subjectCode"
                value={selectedSubjectCode || (deptSubjects.length > 0 ? deptSubjects[0].code : "")}
                onChange={(e) => setSelectedSubjectCode(e.target.value)}
                required
                className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 bg-white outline-none focus:ring-2 focus:ring-cyan-400"
              >
                {deptSubjects.map((s) => (
                  <option key={s.code} value={s.code}>
                    {s.code} - {s.name} - {getComponentDisplay(s.component || "THEORY")}
                  </option>
                ))}
                {deptSubjects.length === 0 && <option value="">No subjects available in this department</option>}
              </select>
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-600 uppercase">Teacher Role *</label>
              <select
                name="role"
                value={assignedRole}
                onChange={(e) => setAssignedRole(e.target.value as "PRIMARY" | "CO-PRIMARY")}
                className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-black text-indigo-900 bg-[#f7fbff] outline-none focus:ring-2 focus:ring-cyan-400"
              >
                <option value="PRIMARY">PRIMARY (Main Course In-Charge)</option>
                <option value="CO-PRIMARY">CO-PRIMARY (Supporting / Lab Faculty)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={deptTeachers.length === 0 || deptSubjects.length === 0}
              className="w-full bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600 text-white font-bold py-2.5 rounded-xl text-xs transition shadow-md shadow-blue-500/25 disabled:opacity-50 flex items-center justify-center gap-1.5"
            >
              + Assign Teacher to Subject
            </button>
          </form>
        </div>
      </div>

      {/* TABLES */}
      {activeTab === "assign" ? (
        <div className="bg-white rounded-2xl border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] overflow-hidden space-y-3">
          <div className="p-5 border-b border-cyan-50 flex flex-wrap justify-between items-center gap-3 bg-[#f7fbff]">
            <div>
              <h3 className="text-sm font-extrabold text-slate-900">Assigned Teachers & Course Ownerships</h3>
              <p className="text-xs text-slate-500 mt-0.5">Filter by specific department to view assigned faculty and subjects</p>
            </div>
            <span className="text-xs bg-blue-50 text-[#0c70d4] border border-blue-200 font-bold px-3 py-1 rounded-full">
              {filteredAssignments.length} Assignments Shown
            </span>
          </div>

          <div className="px-5 pt-2 flex flex-wrap items-center gap-2">
            <span className="text-xs font-extrabold text-slate-500 uppercase tracking-wide mr-1">
              Filter By Department:
            </span>

            <button
              type="button"
              onClick={() => setSelectedDeptFilter("ALL")}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all shadow-xs ${
                selectedDeptFilter === "ALL"
                  ? "bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white ring-2 ring-cyan-300 shadow-blue-500/25"
                  : "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50"
              }`}
            >
              🌐 All Departments ({assignments.length})
            </button>

            {departments.map((dept) => {
              const count = assignments.filter((a) => a.departmentCode === dept.code).length;
              const isSelected = selectedDeptFilter === dept.code;
              return (
                <button
                  key={dept.code}
                  type="button"
                  onClick={() => setSelectedDeptFilter(dept.code)}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all shadow-xs flex items-center gap-1.5 ${
                    isSelected
                      ? "bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white ring-2 ring-cyan-300 shadow-blue-500/25"
                      : "bg-white border border-cyan-200 text-slate-700 hover:bg-blue-50/50"
                  }`}
                >
                  <span>{dept.name}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full font-black ${
                      isSelected ? "bg-white text-blue-700" : "bg-blue-100 text-blue-800"
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-600 font-black border-b border-slate-100 uppercase tracking-wider text-[10px]">
                  <th className="py-3.5 px-6">TEACHER NAME</th>
                  <th className="py-3.5 px-6">EMAIL</th>
                  <th className="py-3.5 px-6">DEPARTMENT</th>
                  <th className="py-3.5 px-6">ASSIGNED SUBJECT</th>
                  <th className="py-3.5 px-6">COMPONENT</th>
                  <th className="py-3.5 px-6">ROLE</th>
                  <th className="py-3.5 px-6 text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredAssignments.map((item) => (
                  <tr key={item.id} className="hover:bg-[#f0f7ff] transition">
                    <td className="py-3.5 px-6 font-bold text-slate-900">{item.teacherName}</td>
                    <td className="py-3.5 px-6 text-slate-500 font-medium">{item.teacherEmail}</td>
                    <td className="py-3.5 px-6 font-mono font-bold text-[#1473e6]">{item.departmentCode}</td>
                    <td className="py-3.5 px-6">
                      <span className="font-extrabold text-slate-800">
                        {item.subjectCode} - {item.subjectName}
                      </span>
                    </td>
                    <td className="py-3.5 px-6">
                      {renderComponentBadge(item.component || "THEORY")}
                    </td>
                    <td className="py-3.5 px-6">
                      <span
                        className={`font-black text-[10px] px-2.5 py-0.5 rounded-full uppercase border ${
                          item.role === "PRIMARY"
                            ? "bg-blue-50 text-blue-700 border-blue-200"
                            : "bg-cyan-50 text-cyan-700 border-cyan-200"
                        }`}
                      >
                        {item.role}
                      </span>
                    </td>
                    <td className="py-3.5 px-6 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setEditingAssignment(item)}
                          className="border border-amber-200 bg-amber-50/70 hover:bg-amber-100 text-amber-700 px-3 py-1 rounded-lg font-bold text-xs transition flex items-center gap-1"
                        >
                          ✏️ Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteAssignment(item.id, item.teacherName, item.subjectCode)}
                          className="border border-rose-200 bg-rose-50/70 hover:bg-rose-100 text-rose-600 px-3 py-1 rounded-lg font-bold text-xs transition flex items-center gap-1"
                        >
                          🗑 Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}

                {filteredAssignments.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-slate-400 font-medium">
                      No teacher assignments found for {selectedDeptFilter === "ALL" ? "any department" : selectedDeptFilter}. Use the form above to add one.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* TEACHERS DIRECTORY */
        <div className="bg-white rounded-2xl border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] overflow-hidden space-y-3">
          <div className="p-5 border-b border-cyan-50 flex justify-between items-center bg-[#f7fbff]">
            <div>
              <h3 className="text-sm font-extrabold text-slate-900">Registered Teachers Directory</h3>
              <p className="text-xs text-slate-500 mt-0.5">Faculty profiles grouped department-wise</p>
            </div>
            <span className="text-xs bg-blue-50 text-[#0c70d4] border border-blue-200 font-bold px-3 py-1 rounded-full">
              {filteredTeachers.length} Teachers Shown
            </span>
          </div>

          <div className="px-5 pt-2 flex flex-wrap items-center gap-2">
            <span className="text-xs font-extrabold text-slate-500 uppercase tracking-wide mr-1">
              Filter By Department:
            </span>

            <button
              type="button"
              onClick={() => setSelectedDeptFilter("ALL")}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all shadow-xs ${
                selectedDeptFilter === "ALL"
                  ? "bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white ring-2 ring-cyan-300 shadow-blue-500/25"
                  : "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50"
              }`}
            >
              🌐 All Departments ({teachersList.length})
            </button>

            {departments.map((dept) => {
              const count = teachersList.filter((t) => t.departmentCode === dept.code).length;
              const isSelected = selectedDeptFilter === dept.code;
              return (
                <button
                  key={dept.code}
                  type="button"
                  onClick={() => setSelectedDeptFilter(dept.code)}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all shadow-xs flex items-center gap-1.5 ${
                    isSelected
                      ? "bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white ring-2 ring-cyan-300 shadow-blue-500/25"
                      : "bg-white border border-cyan-200 text-slate-700 hover:bg-blue-50/50"
                  }`}
                >
                  <span>{dept.name}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full font-black ${
                      isSelected ? "bg-white text-blue-700" : "bg-blue-100 text-blue-800"
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-600 font-black border-b border-slate-100 uppercase tracking-wider text-[10px]">
                  <th className="py-3.5 px-6">TEACHER NAME</th>
                  <th className="py-3.5 px-6">EMAIL</th>
                  <th className="py-3.5 px-6">DEPARTMENT</th>
                  <th className="py-3.5 px-6 text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredTeachers.map((t) => (
                  <tr key={t.id} className="hover:bg-[#f0f7ff] transition">
                    <td className="py-3.5 px-6 font-bold text-slate-900">{t.name}</td>
                    <td className="py-3.5 px-6 text-slate-500 font-medium">{t.email}</td>
                    <td className="py-3.5 px-6 font-mono font-bold text-[#1473e6]">{t.departmentCode}</td>
                    <td className="py-3.5 px-6 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setEditingTeacher(t)}
                          className="border border-amber-200 bg-amber-50/70 hover:bg-amber-100 text-amber-700 px-3 py-1 rounded-lg font-bold text-xs transition flex items-center gap-1"
                        >
                          ✏️ Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteTeacher(t.id, t.name)}
                          className="border border-rose-200 bg-rose-50/70 hover:bg-rose-100 text-rose-600 px-3 py-1 rounded-lg font-bold text-xs transition flex items-center gap-1"
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}

                {filteredTeachers.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-10 text-center text-slate-400 font-medium">
                      No teachers registered in {selectedDeptFilter === "ALL" ? "any department" : selectedDeptFilter}. Use Form 1 to add faculty.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* EDIT MODAL: ASSIGNMENT */}
      {editingAssignment && (
        <div className="fixed inset-0 bg-[#07193b]/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 border border-cyan-100 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3 mb-4">
              <div>
                <h3 className="text-base font-extrabold text-slate-900">Edit Complete Assignment Details</h3>
                <p className="text-xs text-slate-500">Update teacher details, subject, component, and role simultaneously.</p>
              </div>
              <button
                type="button"
                onClick={() => setEditingAssignment(null)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveAssignmentComprehensiveEdit} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Teacher Full Name *</label>
                <input
                  type="text"
                  required
                  value={editingAssignment.teacherName}
                  onChange={(e) =>
                    setEditingAssignment({ ...editingAssignment, teacherName: e.target.value })
                  }
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 outline-none focus:ring-2 focus:ring-cyan-400"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Teacher Email Address *</label>
                <input
                  type="email"
                  required
                  value={editingAssignment.teacherEmail}
                  onChange={(e) =>
                    setEditingAssignment({ ...editingAssignment, teacherEmail: e.target.value })
                  }
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-medium text-slate-900 outline-none focus:ring-2 focus:ring-cyan-400"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Department *</label>
                <select
                  value={editingAssignment.departmentCode}
                  onChange={(e) =>
                    setEditingAssignment({ ...editingAssignment, departmentCode: e.target.value })
                  }
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 bg-[#f7fbff] outline-none"
                >
                  {departments.map((d) => (
                    <option key={d.code} value={d.code}>
                      {d.name} ({d.code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Subject Code *</label>
                  <input
                    type="text"
                    required
                    value={editingAssignment.subjectCode}
                    onChange={(e) =>
                      setEditingAssignment({ ...editingAssignment, subjectCode: e.target.value.toUpperCase() })
                    }
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 uppercase outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Subject Name *</label>
                  <input
                    type="text"
                    required
                    value={editingAssignment.subjectName}
                    onChange={(e) =>
                      setEditingAssignment({ ...editingAssignment, subjectName: e.target.value })
                    }
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Course Component *</label>
                  <select
                    value={editingAssignment.component || "THEORY"}
                    onChange={(e) =>
                      setEditingAssignment({
                        ...editingAssignment,
                        component: e.target.value as CourseComponent,
                      })
                    }
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-indigo-900 bg-[#f7fbff] outline-none"
                  >
                    <option value="THEORY">Theory (TH)</option>
                    <option value="PRACTICAL">Practical / Lab (PR)</option>
                    <option value="TUTORIAL">Tutorial (TUT)</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Faculty Role *</label>
                  <select
                    value={editingAssignment.role}
                    onChange={(e) =>
                      setEditingAssignment({
                        ...editingAssignment,
                        role: e.target.value as "PRIMARY" | "CO-PRIMARY",
                      })
                    }
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-black text-indigo-900 bg-[#f7fbff] outline-none"
                  >
                    <option value="PRIMARY">PRIMARY</option>
                    <option value="CO-PRIMARY">CO-PRIMARY</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setEditingAssignment(null)}
                  className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/25"
                >
                  Save All Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT MODAL: TEACHER */}
      {editingTeacher && (
        <div className="fixed inset-0 bg-[#07193b]/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-cyan-100">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3 mb-4">
              <div>
                <h3 className="text-base font-extrabold text-slate-900">Edit Teacher Profile</h3>
                <p className="text-xs text-slate-500">Updates teacher name, email, and department across all assignments</p>
              </div>
              <button
                type="button"
                onClick={() => setEditingTeacher(null)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveTeacherComprehensiveEdit} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Full Name *</label>
                <input
                  type="text"
                  required
                  value={editingTeacher.name}
                  onChange={(e) => setEditingTeacher({ ...editingTeacher, name: e.target.value })}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 outline-none focus:ring-2 focus:ring-cyan-400"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Email Address *</label>
                <input
                  type="email"
                  required
                  value={editingTeacher.email}
                  onChange={(e) => setEditingTeacher({ ...editingTeacher, email: e.target.value })}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-semibold text-slate-900 outline-none focus:ring-2 focus:ring-cyan-400"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Department *</label>
                <select
                  value={editingTeacher.departmentCode}
                  onChange={(e) => setEditingTeacher({ ...editingTeacher, departmentCode: e.target.value })}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 bg-[#f7fbff] outline-none"
                >
                  {departments.map((d) => (
                    <option key={d.code} value={d.code}>
                      {d.name} ({d.code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setEditingTeacher(null)}
                  className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/25"
                >
                  Save Profile
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}