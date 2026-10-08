import React, { useState, useEffect, type FormEvent } from "react";

type CourseComponent = "THEORY" | "PRACTICAL" | "TUTORIAL";

interface SubjectItem {
  id: string;
  departmentCode: string;
  programCode: string;
  academicYear: "FE" | "SE" | "TE" | "BE";
  type: "CORE" | "ELECTIVE";
  component: CourseComponent;
  code: string;
  name: string;
  credits: number;
}

interface LocalProgram {
  code: string;
  name: string;
  duration?: number;
}

export default function Subjects() {
  const activeInstName = localStorage.getItem("uniadapt_active_institute_name") || "finolex";

  // 1. Departments dynamically loaded from Master Sync
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

  // Re-sync on storage change
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

  const [deptProgramsMap] = useState<Record<string, LocalProgram[]>>(() => {
    const cached = localStorage.getItem("uniadapt_dept_programs_map");
    return cached
      ? JSON.parse(cached)
      : {
          CSE2024: [
            { code: "CS2034", name: "Computer Science & Engineering" },
            { code: "CS2022", name: "B.Tech Computer Science(CYBER)" },
          ],
          CSE2005: [{ code: "CS2022", name: "B.Tech Computer Science(CYBER)" }],
          CSL102: [{ code: "CS2034", name: "cse" }],
          IT2004: [{ code: "IT2024", name: "Information Technology" }],
        };
  });

  // Top Cascading Selection States
  const [selectedDept, setSelectedDept] = useState<string>(departments[0]?.code || "CSE2024");
  const availablePrograms = deptProgramsMap[selectedDept] || [{ code: "DEFAULT", name: "General Engineering" }];
  const [selectedProgram, setSelectedProgram] = useState<string>(availablePrograms[0]?.code || "");
  const [selectedYear, setSelectedYear] = useState<"FE" | "SE" | "TE" | "BE">("FE");

  useEffect(() => {
    const progs = deptProgramsMap[selectedDept] || [];
    if (progs.length > 0) {
      setSelectedProgram(progs[0].code);
    } else {
      setSelectedProgram("");
    }
  }, [selectedDept, deptProgramsMap]);

  // Form 1: Core Subject Form States
  const [coreCode, setCoreCode] = useState("");
  const [coreName, setCoreName] = useState("");
  const [coreCredits, setCoreCredits] = useState<number | "">("");
  const [coreComponent, setCoreComponent] = useState<CourseComponent>("THEORY");

  // Form 2: Elective Subject Form States
  const [elecCode, setElecCode] = useState("");
  const [elecName, setElecName] = useState("");
  const [elecCredits, setElecCredits] = useState<number | "">("");
  const [elecComponent, setElecComponent] = useState<CourseComponent>("THEORY");

  // Popup Toast Notification State
  const [popupMessage, setPopupMessage] = useState<{ text: string; type: "CORE" | "ELECTIVE" } | null>(null);

  // Subject Storage
  const [subjectList, setSubjectList] = useState<SubjectItem[]>(() => {
    const cached = localStorage.getItem("uniadapt_subject_catalogue");
    return cached
      ? JSON.parse(cached)
      : [
          {
            id: "sub-1",
            departmentCode: "CSE2024",
            programCode: "CS2034",
            academicYear: "FE",
            type: "CORE",
            component: "THEORY",
            code: "CS101",
            name: "Engineering Mathematics I",
            credits: 4,
          },
          {
            id: "sub-2",
            departmentCode: "CSE2024",
            programCode: "CS2034",
            academicYear: "FE",
            type: "CORE",
            component: "PRACTICAL",
            code: "CS102P",
            name: "Data Structures Lab",
            credits: 2,
          },
        ];
  });

  const [showTable, setShowTable] = useState<boolean>(true);
  const [editingSubject, setEditingSubject] = useState<SubjectItem | null>(null);

  useEffect(() => {
    localStorage.setItem("uniadapt_subject_catalogue", JSON.stringify(subjectList));
  }, [subjectList]);

  const triggerPopup = (text: string, type: "CORE" | "ELECTIVE") => {
    setPopupMessage({ text, type });
    setTimeout(() => {
      setPopupMessage(null);
    }, 4000);
  };

  const handleAddCoreSubject = (e: FormEvent) => {
    e.preventDefault();
    if (!selectedDept || !selectedProgram || !coreCode.trim() || !coreName.trim()) {
      alert("Please fill all required fields for Core Subject.");
      return;
    }

    const newSub: SubjectItem = {
      id: "sub-" + Date.now(),
      departmentCode: selectedDept,
      programCode: selectedProgram,
      academicYear: selectedYear,
      type: "CORE",
      component: coreComponent,
      code: coreCode.toUpperCase().trim(),
      name: coreName.trim(),
      credits: Number(coreCredits) || 3,
    };

    setSubjectList((prev) => [newSub, ...prev]);
    triggerPopup(`Core ${coreComponent.toLowerCase()} subject "${newSub.code} - ${newSub.name}" added successfully!`, "CORE");

    setCoreCode("");
    setCoreName("");
    setCoreCredits("");
    setCoreComponent("THEORY");
  };

  const handleAddElectiveSubject = (e: FormEvent) => {
    e.preventDefault();
    if (!selectedDept || !selectedProgram || !elecCode.trim() || !elecName.trim()) {
      alert("Please fill all required fields for Elective Subject.");
      return;
    }

    const newSub: SubjectItem = {
      id: "sub-" + Date.now(),
      departmentCode: selectedDept,
      programCode: selectedProgram,
      academicYear: selectedYear,
      type: "ELECTIVE",
      component: elecComponent,
      code: elecCode.toUpperCase().trim(),
      name: elecName.trim(),
      credits: Number(elecCredits) || 3,
    };

    setSubjectList((prev) => [newSub, ...prev]);
    triggerPopup(`Elective ${elecComponent.toLowerCase()} subject "${newSub.code} - ${newSub.name}" added successfully!`, "ELECTIVE");

    setElecCode("");
    setElecName("");
    setElecCredits("");
    setElecComponent("THEORY");
  };

  const handleDeleteSubject = (id: string, name: string) => {
    if (window.confirm(`Delete subject "${name}"?`)) {
      setSubjectList((prev) => prev.filter((s) => s.id !== id));
    }
  };

  const handleSaveEdit = (e: FormEvent) => {
    e.preventDefault();
    if (!editingSubject) return;

    setSubjectList((prev) =>
      prev.map((s) =>
        s.id === editingSubject.id
          ? { ...editingSubject, code: editingSubject.code.toUpperCase().trim() }
          : s
      )
    );
    setEditingSubject(null);
  };

  const filteredSubjects = subjectList.filter(
    (s) =>
      s.departmentCode === selectedDept &&
      (!selectedProgram || s.programCode === selectedProgram) &&
      s.academicYear === selectedYear
  );

  const renderComponentBadge = (comp: CourseComponent) => {
    switch (comp) {
      case "THEORY":
        return (
          <span className="bg-indigo-50 text-indigo-700 border border-indigo-200 font-extrabold text-[10px] px-2 py-0.5 rounded-md">
            📖 Theory (TH)
          </span>
        );
      case "PRACTICAL":
        return (
          <span className="bg-cyan-50 text-cyan-800 border border-cyan-200 font-extrabold text-[10px] px-2 py-0.5 rounded-md">
            🔬 Lab (PR)
          </span>
        );
      case "TUTORIAL":
        return (
          <span className="bg-amber-50 text-amber-800 border border-amber-200 font-extrabold text-[10px] px-2 py-0.5 rounded-md">
            📝 Tutorial (TUT)
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-[#eaf4fe] p-4 sm:p-6 lg:p-8 space-y-6 font-sans text-slate-800">
      {popupMessage && (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50 animate-bounce">
          <div
            className={`flex items-center gap-3 px-6 py-3.5 rounded-2xl shadow-2xl border text-sm font-extrabold text-white ${
              popupMessage.type === "CORE"
                ? "bg-gradient-to-r from-blue-700 via-indigo-700 to-blue-800 border-cyan-300 shadow-blue-900/40"
                : "bg-gradient-to-r from-cyan-600 via-teal-600 to-cyan-700 border-teal-200 shadow-cyan-900/40"
            }`}
          >
            <span className="text-xl">{popupMessage.type === "CORE" ? "📘" : "📙"}</span>
            <span>{popupMessage.text}</span>
            <button
              onClick={() => setPopupMessage(null)}
              className="ml-2 bg-white/20 hover:bg-white/30 rounded-full w-5 h-5 flex items-center justify-center text-xs"
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
                CURRICULUM ENGINE
              </span>
              <span className="text-cyan-300 text-xs font-bold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                {activeInstName}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
              Subject Catalogue & Syllabus Setup
            </h1>
            <p className="text-xs sm:text-sm text-cyan-100/80 mt-0.5">
              Configure Theory lectures, Practical labs, and Tutorials with proper credit weights.
            </p>
          </div>
        </div>
      </div>

      {/* CASCADING SELECTOR BAR */}
      <div className="bg-white rounded-2xl p-5 border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)]">
        <span className="text-[10px] font-black tracking-widest text-[#0c70d4] uppercase block mb-3">
          1. CHOOSE ACADEMIC CONTEXT (DEPARTMENT &bull; DEGREE &bull; YEAR)
        </span>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-xs font-bold text-slate-700 block mb-1">Select Department *</label>
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 bg-[#f7fbff] outline-none focus:ring-2 focus:ring-cyan-400 shadow-2xs"
            >
              {departments.map((d) => (
                <option key={d.code} value={d.code}>
                  {d.name} ({d.code})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 block mb-1">Select Program (Degree) *</label>
            <select
              value={selectedProgram}
              onChange={(e) => setSelectedProgram(e.target.value)}
              className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 bg-[#f7fbff] outline-none focus:ring-2 focus:ring-cyan-400 shadow-2xs"
            >
              {availablePrograms.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.name} ({p.code})
                </option>
              ))}
              {availablePrograms.length === 0 && <option value="">No programs available</option>}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 block mb-1">Select Year Level *</label>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value as any)}
              className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-black text-[#0c70d4] bg-[#f7fbff] outline-none focus:ring-2 focus:ring-cyan-400 shadow-2xs"
            >
              <option value="FE">FE (First Year - Sem 1 & 2)</option>
              <option value="SE">SE (Second Year - Sem 3 & 4)</option>
              <option value="TE">TE (Third Year - Sem 5 & 6)</option>
              <option value="BE">BE (Final Year - Sem 7 & 8)</option>
            </select>
          </div>
        </div>
      </div>

      {/* FORMS: ADD CORE & ELECTIVE */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CORE FORM */}
        <div className="bg-white rounded-2xl p-6 border border-blue-200 shadow-[0_4px_20px_rgba(20,115,230,0.06)] space-y-4">
          <div className="flex items-center gap-3 border-b border-blue-100 pb-3">
            <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200 text-blue-700 font-black flex items-center justify-center text-lg">
              📘
            </div>
            <div>
              <h3 className="font-extrabold text-slate-900 text-sm">Add Core Subject</h3>
              <p className="text-[11px] text-slate-500">Compulsory curriculum for {selectedYear}</p>
            </div>
            <span className="ml-auto bg-blue-100 text-blue-800 font-extrabold text-[10px] px-2.5 py-1 rounded-full uppercase">
              CORE
            </span>
          </div>

          <form onSubmit={handleAddCoreSubject} className="space-y-3.5">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-bold text-slate-600 uppercase">Subject Code *</label>
                <input
                  type="text"
                  placeholder="e.g. CS101 or CS101P"
                  value={coreCode}
                  onChange={(e) => setCoreCode(e.target.value)}
                  required
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 uppercase font-bold text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-600 uppercase">Course Component *</label>
                <select
                  value={coreComponent}
                  onChange={(e) => setCoreComponent(e.target.value as CourseComponent)}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-bold text-indigo-900 bg-[#f7fbff] outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="THEORY">Theory Lecture (TH)</option>
                  <option value="PRACTICAL">Practical / Lab (PR)</option>
                  <option value="TUTORIAL">Tutorial (TUT)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-600 uppercase">Subject Name *</label>
              <input
                type="text"
                placeholder="e.g. Data Structures & Algorithms"
                value={coreName}
                onChange={(e) => setCoreName(e.target.value)}
                required
                className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-semibold text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-600 uppercase">Credits *</label>
              <input
                type="number"
                min={1}
                max={10}
                placeholder="e.g. 4 for Theory, 2 for Lab"
                value={coreCredits}
                onChange={(e) => setCoreCredits(e.target.value ? Number(e.target.value) : "")}
                required
                className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-bold text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <button
              type="submit"
              className="w-full bg-gradient-to-r from-[#1d63ea] to-[#0295e6] hover:from-[#1554cd] hover:to-[#0284cc] text-white font-bold py-2.5 rounded-xl text-xs transition shadow-md shadow-blue-500/25 flex items-center justify-center gap-1.5"
            >
              + Add Core Subject
            </button>
          </form>
        </div>

        {/* ELECTIVE FORM */}
        <div className="bg-white rounded-2xl p-6 border border-cyan-200 shadow-[0_4px_20px_rgba(20,115,230,0.06)] space-y-4">
          <div className="flex items-center gap-3 border-b border-cyan-100 pb-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-50 border border-cyan-200 text-cyan-700 font-black flex items-center justify-center text-lg">
              📙
            </div>
            <div>
              <h3 className="font-extrabold text-slate-900 text-sm">Add Elective Subject</h3>
              <p className="text-[11px] text-slate-500">Choice-based course for {selectedYear}</p>
            </div>
            <span className="ml-auto bg-cyan-100 text-cyan-800 font-extrabold text-[10px] px-2.5 py-1 rounded-full uppercase">
              ELECTIVE
            </span>
          </div>

          <form onSubmit={handleAddElectiveSubject} className="space-y-3.5">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-bold text-slate-600 uppercase">Elective Code *</label>
                <input
                  type="text"
                  placeholder="e.g. ELEC201 or CS501"
                  value={elecCode}
                  onChange={(e) => setElecCode(e.target.value)}
                  required
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 uppercase font-bold text-slate-900 outline-none focus:ring-2 focus:ring-cyan-500"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-600 uppercase">Course Component *</label>
                <select
                  value={elecComponent}
                  onChange={(e) => setElecComponent(e.target.value as CourseComponent)}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-bold text-cyan-900 bg-[#f7fbff] outline-none focus:ring-2 focus:ring-cyan-500"
                >
                  <option value="THEORY">Theory Lecture (TH)</option>
                  <option value="PRACTICAL">Practical / Lab (PR)</option>
                  <option value="TUTORIAL">Tutorial (TUT)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-600 uppercase">Subject Name *</label>
              <input
                type="text"
                placeholder="e.g. Cloud Computing Architecture"
                value={elecName}
                onChange={(e) => setElecName(e.target.value)}
                required
                className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-semibold text-slate-900 outline-none focus:ring-2 focus:ring-cyan-500"
              />
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-600 uppercase">Credits *</label>
              <input
                type="number"
                min={1}
                max={10}
                placeholder="e.g. 3"
                value={elecCredits}
                onChange={(e) => setElecCredits(e.target.value ? Number(e.target.value) : "")}
                required
                className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-bold text-slate-900 outline-none focus:ring-2 focus:ring-cyan-500"
              />
            </div>

            <button
              type="submit"
              className="w-full bg-gradient-to-r from-cyan-600 to-teal-500 hover:from-cyan-700 hover:to-teal-600 text-white font-bold py-2.5 rounded-xl text-xs transition shadow-md shadow-cyan-500/25 flex items-center justify-center gap-1.5"
            >
              + Add Elective Subject
            </button>
          </form>
        </div>
      </div>

      {/* TABLE */}
      <div className="bg-white rounded-2xl border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] overflow-hidden">
        <div className="p-5 border-b border-cyan-50 flex flex-wrap justify-between items-center gap-3 bg-[#f7fbff]">
          <div>
            <h2 className="text-base font-extrabold text-slate-900">
              Departmental Subjects: <span className="text-[#0c70d4]">{selectedDept}</span> &bull; {selectedYear}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Review course components (TH / PR / TUT), types, credits, or make edits.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setShowTable(!showTable)}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white text-xs font-bold shadow-md shadow-blue-500/20 hover:scale-[1.02] transition"
          >
            {showTable
              ? `Hide Added Subjects (${filteredSubjects.length})`
              : `View Added Subjects (${filteredSubjects.length})`}
          </button>
        </div>

        {showTable && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-600 font-black border-b border-slate-100 uppercase tracking-wider text-[10px]">
                  <th className="py-3.5 px-6">TYPE</th>
                  <th className="py-3.5 px-6">COMPONENT</th>
                  <th className="py-3.5 px-6">CODE</th>
                  <th className="py-3.5 px-6">SUBJECT NAME</th>
                  <th className="py-3.5 px-6">CREDITS</th>
                  <th className="py-3.5 px-6">PROGRAM & YEAR</th>
                  <th className="py-3.5 px-6 text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredSubjects.map((sub) => (
                  <tr key={sub.id} className="hover:bg-[#f0f7ff] transition">
                    <td className="py-3.5 px-6">
                      <span
                        className={`font-black text-[10px] px-2.5 py-0.5 rounded-full uppercase border ${
                          sub.type === "CORE"
                            ? "bg-blue-50 text-blue-700 border-blue-200"
                            : "bg-cyan-50 text-cyan-700 border-cyan-200"
                        }`}
                      >
                        {sub.type}
                      </span>
                    </td>
                    <td className="py-3.5 px-6">
                      {renderComponentBadge(sub.component || "THEORY")}
                    </td>
                    <td className="py-3.5 px-6 font-mono font-bold text-[#1473e6]">{sub.code}</td>
                    <td className="py-3.5 px-6 font-bold text-slate-900">{sub.name}</td>
                    <td className="py-3.5 px-6">
                      <span className="font-extrabold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                        {sub.credits} Credits
                      </span>
                    </td>
                    <td className="py-3.5 px-6 text-slate-600 font-medium">
                      <span className="font-bold text-indigo-700">{sub.academicYear}</span> ({sub.programCode})
                    </td>
                    <td className="py-3.5 px-6 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setEditingSubject(sub)}
                          className="border border-amber-200 bg-amber-50/70 hover:bg-amber-100 text-amber-700 px-3 py-1 rounded-lg font-bold text-xs transition"
                        >
                          ✏️ Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteSubject(sub.id, sub.name)}
                          className="border border-rose-200 bg-rose-50/70 hover:bg-rose-100 text-rose-600 px-3 py-1 rounded-lg font-bold text-xs transition"
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}

                {filteredSubjects.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-slate-400 font-medium">
                      No subjects added yet for {selectedDept} ({selectedYear}). Use the forms above to add Core or Elective courses.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* EDIT MODAL */}
      {editingSubject && (
        <div className="fixed inset-0 bg-[#07193b]/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-cyan-100">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3 mb-4">
              <h3 className="text-base font-extrabold text-slate-900">Edit Subject Details</h3>
              <button
                type="button"
                onClick={() => setEditingSubject(null)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleSaveEdit} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-600">Subject Code *</label>
                <input
                  type="text"
                  required
                  value={editingSubject.code}
                  onChange={(e) => setEditingSubject({ ...editingSubject, code: e.target.value })}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 uppercase font-bold text-slate-900 outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600">Subject Name *</label>
                <input
                  type="text"
                  required
                  value={editingSubject.name}
                  onChange={(e) => setEditingSubject({ ...editingSubject, name: e.target.value })}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-semibold text-slate-900 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-600">Credits *</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    required
                    value={editingSubject.credits}
                    onChange={(e) => setEditingSubject({ ...editingSubject, credits: Number(e.target.value) })}
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-bold text-slate-900 outline-none"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-600">Component *</label>
                  <select
                    value={editingSubject.component || "THEORY"}
                    onChange={(e) => setEditingSubject({ ...editingSubject, component: e.target.value as CourseComponent })}
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-bold text-slate-900 outline-none"
                  >
                    <option value="THEORY">Theory (TH)</option>
                    <option value="PRACTICAL">Practical / Lab (PR)</option>
                    <option value="TUTORIAL">Tutorial (TUT)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600">Subject Type *</label>
                <select
                  value={editingSubject.type}
                  onChange={(e) => setEditingSubject({ ...editingSubject, type: e.target.value as any })}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-bold text-slate-900 outline-none"
                >
                  <option value="CORE">CORE (Compulsory)</option>
                  <option value="ELECTIVE">ELECTIVE (Choice Based)</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setEditingSubject(null)}
                  className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white rounded-xl text-xs font-bold hover:from-[#1554cd] hover:to-[#0284cc] shadow-md shadow-blue-500/25"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}