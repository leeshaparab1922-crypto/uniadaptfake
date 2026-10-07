import { useState, useEffect, type FormEvent } from "react";
import {
  useCreateBatch,
  useCreateDepartment,
  useCreateInstitute,
  useCreateProgram,
  useCreateSection,
  useCreateSemester,
  useBatches,
  useDepartments,
  useInstitutes,
  usePrograms,
  useSections,
  useSemesters,
} from "../../api/academicStructureApi";
import { useNotify } from "../../hooks/useNotify";

interface LocalClassCapacity {
  className: "FE" | "SE" | "TE" | "BE";
  capacity: number;
}

interface LocalProgram {
  code: string;
  name: string;
  duration?: number;
}

interface FullEditState {
  deptId: string;
  deptCode: string;
  deptName: string;
  programCode: string;
  programName: string;
  className: "FE" | "SE" | "TE" | "BE";
  capacity: number;
}

export default function HierarchyManager() {
  const createInstitute = useCreateInstitute();
  const createDepartment = useCreateDepartment();
  const createProgram = useCreateProgram();
  const createBatch = useCreateBatch();
  const createSemester = useCreateSemester();
  const createSection = useCreateSection();
  const notify = useNotify();

  const [instituteId, setInstituteId] = useState<string>(() => {
    return localStorage.getItem("uniadapt_active_institute_id") || "";
  });
  const [departmentId, setDepartmentId] = useState("");
  const [programId, setProgramId] = useState("");
  const [batchId, setBatchId] = useState("");
  const [semesterId, setSemesterId] = useState("");

  const [activeDrilldownDept, setActiveDrilldownDept] = useState<{ id: string; code: string; name: string } | null>(null);
  const [selectedClassLevel, setSelectedClassLevel] = useState<'SE' | 'TE' | 'BE' | 'FE'>('SE');

  // Term dates retrieval dynamically synced from uploaded calendar PDF
  const getAutoTermDates = (level: 'SE' | 'TE' | 'BE' | 'FE') => {
    if (level === 'FE') {
      const cachedFE = localStorage.getItem('uniadapt_term_dates_FE');
      return cachedFE ? JSON.parse(cachedFE) : { start: '01-09-2026', end: '31-12-2026' };
    }
    const cachedSE = localStorage.getItem('uniadapt_term_dates_SE_TE_BE');
    return cachedSE ? JSON.parse(cachedSE) : { start: '06-07-2026', end: '17-10-2026' };
  };

  const autoDates = getAutoTermDates(selectedClassLevel);

  const [deletedDeptIds, setDeletedDeptIds] = useState<string[]>(() => {
    const cached = localStorage.getItem("uniadapt_deleted_dept_ids");
    return cached ? JSON.parse(cached) : [];
  });

  const [deletedInstIds, setDeletedInstIds] = useState<string[]>(() => {
    const cached = localStorage.getItem("uniadapt_deleted_inst_ids");
    return cached ? JSON.parse(cached) : [];
  });

  const [customDeptNames, setCustomDeptNames] = useState<Record<string, { name: string; code: string }>>(() => {
    const cached = localStorage.getItem("uniadapt_edited_depts");
    return cached ? JSON.parse(cached) : {};
  });

  // Department-to-Classes Map (FE, SE, TE, BE with Capacity)
  const [deptClassesMap, setDeptClassesMap] = useState<Record<string, LocalClassCapacity[]>>(() => {
    const cached = localStorage.getItem("uniadapt_dept_classes_map");
    if (cached) {
      try {
        return JSON.parse(cached);
      } catch (e) {
        console.error(e);
      }
    }
    return {
      CSE2024: [
        { className: "FE", capacity: 60 },
        { className: "SE", capacity: 70 },
        { className: "TE", capacity: 60 },
        { className: "BE", capacity: 60 },
      ],
      CSE2005: [
        { className: "FE", capacity: 60 },
        { className: "SE", capacity: 60 },
      ],
      CSL102: [{ className: "SE", capacity: 60 }],
      IT2004: [{ className: "SE", capacity: 70 }],
    };
  });

  const [deptProgramsMap, setDeptProgramsMap] = useState<Record<string, LocalProgram[]>>(() => {
    const cached = localStorage.getItem("uniadapt_dept_programs_map");
    return cached
      ? JSON.parse(cached)
      : {
          CSE2024: [{ code: "CS2034", name: "Computer Science & Engineering", duration: 8 }],
          CSE2005: [{ code: "CS2022", name: "B.Tech Computer Science(CYBER)", duration: 8 }],
          CSL102: [{ code: "CS2034", name: "cse", duration: 8 }],
          IT2004: [{ code: "IT2024", name: "Information Technology", duration: 8 }],
        };
  });

  const [activeTab, setActiveTab] = useState<"table" | "create">("table");
  const [comprehensiveEdit, setComprehensiveEdit] = useState<FullEditState | null>(null);
  const [editInstModal, setEditInstModal] = useState<{ id: string; name: string } | null>(null);

  // New Class Form State for Card 6
  const [newClassInput, setNewClassInput] = useState<{ className: "FE" | "SE" | "TE" | "BE"; capacity: number }>({
    className: "SE",
    capacity: 70,
  });

  const institutes = useInstitutes();
  const departments = useDepartments(instituteId);
  const programs = usePrograms(departmentId);
  const batches = useBatches(programId);
  const semesters = useSemesters(batchId);
  const sections = useSections(semesterId);

  const instituteList = (institutes.data ?? []).filter((i) => !deletedInstIds.includes(i.id));
  const activeInst = instituteList.find((i) => i.id === instituteId);
  const effectiveInstId = instituteId;

  useEffect(() => {
    localStorage.setItem("uniadapt_deleted_dept_ids", JSON.stringify(deletedDeptIds));
  }, [deletedDeptIds]);

  useEffect(() => {
    localStorage.setItem("uniadapt_deleted_inst_ids", JSON.stringify(deletedInstIds));
  }, [deletedInstIds]);

  useEffect(() => {
    localStorage.setItem("uniadapt_edited_depts", JSON.stringify(customDeptNames));
  }, [customDeptNames]);

  useEffect(() => {
    localStorage.setItem("uniadapt_dept_classes_map", JSON.stringify(deptClassesMap));
  }, [deptClassesMap]);

  useEffect(() => {
    localStorage.setItem("uniadapt_dept_programs_map", JSON.stringify(deptProgramsMap));
  }, [deptProgramsMap]);

  const isStrictAlphanumeric = (val: string): boolean => {
    const hasLetter = /[a-zA-Z]/.test(val);
    const hasNumber = /[0-9]/.test(val);
    const validChars = /^[a-zA-Z0-9_-]+$/.test(val);
    return hasLetter && hasNumber && validChars;
  };

  const departmentList = (departments.data ?? [])
    .filter((d) => !deletedDeptIds.includes(d.id))
    .map((d) => {
      if (customDeptNames[d.id]) {
        return {
          ...d,
          name: customDeptNames[d.id].name,
          code: customDeptNames[d.id].code,
        };
      }
      return d;
    });

  function pickInstitute(id: string) {
    const inst = instituteList.find((i) => i.id === id);
    setInstituteId(id);
    localStorage.setItem("uniadapt_active_institute_id", id);
    localStorage.setItem("uniadapt_active_institute_name", inst ? inst.name : "");
    setDepartmentId("");
    setProgramId("");
    setBatchId("");
    setSemesterId("");
    setActiveDrilldownDept(null);
  }

  function pickDepartment(id: string) {
    setDepartmentId(id);
    setProgramId("");
    setBatchId("");
    setSemesterId("");
  }

  function submitInstitute(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    const instName = String(form.get("name")).trim();
    const stateVal = String(form.get("state") || "Maharashtra").trim();

    createInstitute.mutate(
      { name: instName, timezone: stateVal },
      {
        onSuccess: (data) => {
          pickInstitute(data.id);
          formEl.reset();
          notify.success(`Institute "${instName}" created successfully.`);
        },
        onError: notify.error,
      }
    );
  }

  function submitDepartment(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!effectiveInstId) {
      alert("Please select an institute first.");
      return;
    }
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    const code = String(form.get("code")).toUpperCase().trim();
    const name = String(form.get("name")).trim();

    if (!isStrictAlphanumeric(code)) {
      alert("Validation Error: Dept Code must be an alphanumeric combination (e.g. CSE2024 or IT2004).");
      return;
    }

    setDeptProgramsMap((prev) => ({
      ...prev,
      [code]: [{ code: "CS2034", name, duration: 8 }],
    }));
    setDeptClassesMap((prev) => ({
      ...prev,
      [code]: [
        { className: "FE", capacity: 60 },
        { className: "SE", capacity: 60 },
      ],
    }));

    createDepartment.mutate(
      { institute_id: effectiveInstId, code, name },
      {
        onSuccess: (data) => {
          pickDepartment(data.id);
          formEl.reset();
          notify.success(`Department "${code} - ${name}" created successfully.`);
        },
        onError: notify.error,
      }
    );
  }

  function submitAddClassCapacity(e: FormEvent) {
    e.preventDefault();
    const targetDept = departmentList.find((d) => d.id === departmentId) || departmentList[0];
    if (!targetDept) {
      alert("Please select or create a department first.");
      return;
    }

    const currentClasses = deptClassesMap[targetDept.code] || [];
    const filtered = currentClasses.filter((c) => c.className !== newClassInput.className);

    setDeptClassesMap((prev) => ({
      ...prev,
      [targetDept.code]: [...filtered, newClassInput],
    }));

    notify.success(`Class ${newClassInput.className} (Capacity: ${newClassInput.capacity} seats) saved.`);
  }

  function submitSemesterWithAutoDates() {
    const dates = getAutoTermDates(selectedClassLevel);
    createSemester.mutate(
      {
        batch_id: batchId || "default-batch",
        number: selectedClassLevel === 'FE' ? 1 : selectedClassLevel === 'SE' ? 3 : selectedClassLevel === 'TE' ? 5 : 7,
        start_date: dates.start,
        end_date: dates.end,
      },
      {
        onSuccess: (data) => {
          setSemesterId(data.id);
          notify.success(`Applied ${selectedClassLevel} term dates: ${dates.start} to ${dates.end}`);
        },
        onError: notify.error,
      }
    );
  }

  function handleDeleteDepartment(id: string, name: string) {
    if (window.confirm(`Delete department "${name}"?`)) {
      setDeletedDeptIds((prev) => [...prev, id]);
      if (departmentId === id) setDepartmentId("");
      if (activeDrilldownDept?.id === id) setActiveDrilldownDept(null);
      notify.success(`Department "${name}" deleted.`);
    }
  }

  function handleDeleteInstitute(id: string, name: string) {
    if (window.confirm(`Delete institute "${name}"?`)) {
      setDeletedInstIds((prev) => [...prev, id]);
      if (instituteId === id) {
        setInstituteId("");
        localStorage.removeItem("uniadapt_active_institute_id");
        localStorage.removeItem("uniadapt_active_institute_name");
      }
      setActiveDrilldownDept(null);
      notify.success(`Institute "${name}" deleted.`);
    }
  }

  // Open Edit Modal with Class and Capacity
  function openComprehensiveEdit(dept: { id: string; code: string; name: string }) {
    const progList = deptProgramsMap[dept.code] || [];
    const classList = deptClassesMap[dept.code] || [];

    setComprehensiveEdit({
      deptId: dept.id,
      deptCode: dept.code,
      deptName: dept.name,
      programCode: progList[0]?.code || "CS2034",
      programName: progList[0]?.name || "Computer Science & Engineering",
      className: classList[0]?.className || "SE",
      capacity: classList[0]?.capacity || 70,
    });
  }

  function handleSaveComprehensiveEdit(e: FormEvent) {
    e.preventDefault();
    if (!comprehensiveEdit) return;

    if (!isStrictAlphanumeric(comprehensiveEdit.deptCode)) {
      alert("Validation Error: Dept Code must contain both letters and numbers.");
      return;
    }

    const oldCode = departmentList.find((d) => d.id === comprehensiveEdit.deptId)?.code || comprehensiveEdit.deptCode;
    const newCode = comprehensiveEdit.deptCode.toUpperCase().trim();

    // 1. Department Name/Code
    setCustomDeptNames((prev) => ({
      ...prev,
      [comprehensiveEdit.deptId]: {
        name: comprehensiveEdit.deptName.trim(),
        code: newCode,
      },
    }));

    // 2. Program Details
    setDeptProgramsMap((prev) => {
      const nextMap = { ...prev };
      if (oldCode !== newCode) delete nextMap[oldCode];
      nextMap[newCode] = [
        {
          code: comprehensiveEdit.programCode.toUpperCase().trim(),
          name: comprehensiveEdit.programName.trim(),
          duration: 8,
        },
      ];
      return nextMap;
    });

    // 3. Class (FE/SE/TE/BE) & Capacity
    setDeptClassesMap((prev) => {
      const nextMap = { ...prev };
      const currentArr = (oldCode !== newCode ? prev[oldCode] : prev[newCode]) || [];
      const updatedArr = currentArr.filter((c) => c.className !== comprehensiveEdit.className);
      
      if (oldCode !== newCode) delete nextMap[oldCode];
      nextMap[newCode] = [
        ...updatedArr,
        {
          className: comprehensiveEdit.className,
          capacity: Number(comprehensiveEdit.capacity) || 70,
        },
      ];
      return nextMap;
    });

    if (activeDrilldownDept?.id === comprehensiveEdit.deptId) {
      setActiveDrilldownDept({
        id: comprehensiveEdit.deptId,
        code: newCode,
        name: comprehensiveEdit.deptName.trim(),
      });
    }

    notify.success("Department, Program, Class Level, and Capacity updated successfully!");
    setComprehensiveEdit(null);
  }

  return (
    <div className="min-h-screen bg-[#eaf4fe] p-4 sm:p-6 lg:p-8 space-y-6 font-sans text-slate-800" data-testid="hierarchy-manager">
      {/* HERO BANNER (Sky-Blue Accent + Deep Navy Theme) */}
      <div className="relative overflow-hidden rounded-[24px] bg-gradient-to-r from-[#07193b] via-[#09295e] to-[#04122d] border border-cyan-400/40 p-6 sm:p-7 shadow-xl shadow-blue-950/20">
        <div className="absolute -top-16 -right-16 w-80 h-80 bg-cyan-400/20 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="bg-[#0e3b79] text-cyan-300 border border-cyan-400/40 text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                ADMINISTRATION CORE
              </span>
              <span className="text-cyan-300 text-xs font-bold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                {activeInst?.name || "Global Scope"}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
              Academic Structure & Hierarchy
            </h1>
            <p className="text-xs sm:text-sm text-cyan-100/80 mt-0.5">
              Configure engineering departments, programs, and manage class-level capacities (FE, SE, TE, BE).
            </p>
          </div>

          <div className="flex items-center gap-2 bg-[#092557] border border-cyan-400/30 p-1.5 rounded-2xl">
            <button
              type="button"
              onClick={() => {
                setActiveTab("table");
                setActiveDrilldownDept(null);
              }}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
                activeTab === "table"
                  ? "bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white shadow-md shadow-blue-500/25"
                  : "text-cyan-200 hover:text-white"
              }`}
            >
              📋 View Saved Hierarchy Table
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab("create");
                setActiveDrilldownDept(null);
              }}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
                activeTab === "create"
                  ? "bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white shadow-md shadow-blue-500/25"
                  : "text-cyan-200 hover:text-white"
              }`}
            >
              ➕ Setup & Add Entities
            </button>
          </div>
        </div>
      </div>

      {/* INSTITUTE SELECTOR BAR */}
      <div className="bg-white rounded-2xl p-4 sm:p-5 border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-black tracking-widest text-[#0c70d4] uppercase">
            SELECTED INSTITUTE:
          </span>
          <select
            value={instituteId}
            onChange={(e) => pickInstitute(e.target.value)}
            className="border border-cyan-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-900 bg-[#f7fbff] outline-none focus:ring-2 focus:ring-cyan-400 shadow-2xs"
          >
            <option value="" disabled className="text-slate-400">
              -- Select Institute --
            </option>
            {instituteList.map((inst) => (
              <option key={inst.id} value={inst.id}>
                🏫 {inst.name} ({inst.timezone || "Maharashtra"})
              </option>
            ))}
          </select>
        </div>

        {activeInst && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setEditInstModal({ id: activeInst.id, name: activeInst.name })}
              className="border border-cyan-200 bg-[#f7fbff] hover:bg-cyan-50 text-[#0c70d4] px-3.5 py-1.5 rounded-xl text-xs font-bold transition"
            >
              ✏ Edit Institute
            </button>
            <button
              type="button"
              onClick={() => handleDeleteInstitute(activeInst.id, activeInst.name)}
              className="border border-rose-200 bg-rose-50/70 hover:bg-rose-100 text-rose-600 px-3.5 py-1.5 rounded-xl text-xs font-bold transition"
            >
              🗑 Delete Institute
            </button>
          </div>
        )}
      </div>

      {/* ===================== TAB 1: SAVED DETAILS VIEW ===================== */}
      {activeTab === "table" && (
        <>
          {activeDrilldownDept ? (
            <div className="bg-white rounded-2xl border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] overflow-hidden p-6 space-y-6">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-cyan-100 pb-5">
                <div>
                  <button
                    onClick={() => setActiveDrilldownDept(null)}
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-[#0c70d4] hover:text-blue-800 bg-[#f0f7ff] border border-cyan-200 px-3 py-1.5 rounded-xl transition mb-2"
                  >
                    ⬅ Back to Departments Table
                  </button>
                  <div className="flex items-center gap-3">
                    <h2 className="text-xl font-black text-slate-900">{activeDrilldownDept.name}</h2>
                    <span className="font-mono bg-blue-50 text-[#1473e6] border border-blue-200 font-extrabold px-2.5 py-0.5 rounded text-xs">
                      {activeDrilldownDept.code}
                    </span>
                    <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold px-2 py-0.5 rounded text-xs">
                      ● Active Department
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Institute: <strong className="text-slate-700">{activeInst?.name}</strong> &bull; Class Breakdown (FE, SE, TE, BE)
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => openComprehensiveEdit(activeDrilldownDept)}
                  className="border border-cyan-200 bg-[#f7fbff] hover:bg-cyan-50 text-[#0c70d4] px-4 py-2 rounded-xl font-bold text-xs transition"
                >
                  ✏ Edit Details
                </button>
              </div>

              {/* Department Structure Cards */}
              <div className="space-y-6">
                {(deptProgramsMap[activeDrilldownDept.code] || [
                  { code: "CS2034", name: "Computer Science & Engineering", duration: 8 },
                ]).map((prog, pIdx) => {
                  const currentClasses = deptClassesMap[activeDrilldownDept.code] || [
                    { className: "FE", capacity: 60 },
                    { className: "SE", capacity: 70 },
                  ];
                  const seDates = getAutoTermDates('SE');
                  const feDates = getAutoTermDates('FE');

                  return (
                    <div
                      key={pIdx}
                      className="border border-cyan-100 rounded-2xl bg-[#f7fbff] p-5 shadow-2xs space-y-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cyan-100 pb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">🎓</span>
                          <div>
                            <h3 className="text-sm font-black text-slate-900">{prog.name}</h3>
                            <span className="text-xs text-slate-500 font-medium">
                              Program Code: <strong className="text-[#1473e6]">{prog.code}</strong> &bull; Duration: {prog.duration || 8} Semesters
                            </span>
                          </div>
                        </div>
                        <span className="text-xs bg-cyan-100 text-cyan-900 border border-cyan-200 font-extrabold px-3 py-1 rounded-full uppercase">
                          Enrolled Batches Active
                        </span>
                      </div>

                      {/* Classes & Capacities Breakdown */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Senior Classes (SE / TE / BE) */}
                        <div className="bg-white border border-cyan-100 rounded-xl p-4 shadow-2xs space-y-3">
                          <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-base">📅</span>
                              <h4 className="text-xs font-black text-slate-800">Senior Classes (SE, TE, BE)</h4>
                            </div>
                            <span className="text-[10px] bg-blue-50 text-blue-700 border border-blue-200 font-bold px-2 py-0.5 rounded">
                              Term: {seDates.start} to {seDates.end}
                            </span>
                          </div>

                          <div className="space-y-2">
                            <div className="bg-[#f7fbff] border border-cyan-100 rounded-lg p-3 space-y-2">
                              <span className="text-[10px] font-black text-[#0c70d4] uppercase tracking-wider block">
                                Configured Class Intake
                              </span>
                              <div className="flex flex-wrap gap-2">
                                {currentClasses
                                  .filter((c) => c.className !== "FE")
                                  .map((c, idx) => (
                                    <div
                                      key={idx}
                                      className="bg-white border border-cyan-200 rounded-lg px-3 py-1.5 shadow-2xs flex items-center gap-2"
                                    >
                                      <span className="font-black text-[#0c70d4] text-xs">Class {c.className}</span>
                                      <span className="text-slate-300">|</span>
                                      <span className="text-xs font-bold text-slate-700">{c.capacity} Seats Capacity</span>
                                    </div>
                                  ))}
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* First Year Class (FE) */}
                        <div className="bg-white border border-cyan-100 rounded-xl p-4 shadow-2xs space-y-3">
                          <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-base">🎓</span>
                              <h4 className="text-xs font-black text-slate-800">First Year (FE Class)</h4>
                            </div>
                            <span className="text-[10px] bg-cyan-50 text-cyan-800 border border-cyan-200 font-bold px-2 py-0.5 rounded">
                              Term: {feDates.start} to {feDates.end}
                            </span>
                          </div>

                          <div className="space-y-2">
                            <div className="bg-[#f7fbff] border border-cyan-100 rounded-lg p-3 space-y-2">
                              <span className="text-[10px] font-black text-cyan-800 uppercase tracking-wider block">
                                FE Intake Capacity
                              </span>
                              <div className="flex flex-wrap gap-2">
                                {currentClasses
                                  .filter((c) => c.className === "FE")
                                  .map((c, idx) => (
                                    <div
                                      key={idx}
                                      className="bg-white border border-cyan-200 rounded-lg px-3 py-1.5 shadow-2xs flex items-center gap-2"
                                    >
                                      <span className="font-black text-cyan-800 text-xs">Class FE</span>
                                      <span className="text-slate-300">|</span>
                                      <span className="text-xs font-bold text-slate-700">{c.capacity} Seats Capacity</span>
                                    </div>
                                  ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            /* Main Departments Table */
            <div className="bg-white rounded-2xl border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] overflow-hidden">
              <div className="p-5 border-b border-cyan-50 flex flex-wrap justify-between items-center gap-3 bg-[#f7fbff]">
                <div>
                  <h2 className="text-base font-extrabold text-slate-900">
                    Departmental Breakdown &bull; <span className="text-[#0c70d4]">{activeInst ? activeInst.name : "No Institute Selected"}</span>
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Click on any department name to view its detailed programs, classes (FE, SE, TE, BE), and capacities.
                  </p>
                </div>
                {activeInst && (
                  <span className="text-[11px] bg-blue-100 text-blue-900 font-extrabold px-3 py-1 rounded-full uppercase border border-blue-200">
                    {departmentList.length} Departments Active
                  </span>
                )}
              </div>

              {!instituteId ? (
                <div className="py-12 px-4 text-center">
                  <span className="text-3xl mb-2 block">🏫</span>
                  <h3 className="text-sm font-bold text-slate-700">Please Select an Institute</h3>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                    Select an institution from the dropdown above to view its registered academic departments.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="bg-slate-50 text-slate-600 font-black border-b border-slate-100 uppercase tracking-wider text-[10px]">
                        <th className="py-3.5 px-6">DEPT CODE</th>
                        <th className="py-3.5 px-6">DEPARTMENT NAME (CLICK TO VIEW)</th>
                        <th className="py-3.5 px-6">STATUS</th>
                        <th className="py-3.5 px-6">ACTIVE PROGRAMS</th>
                        <th className="py-3.5 px-6 text-right">ACTION</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {departmentList.map((dept) => {
                        const codeKey = dept.code.toUpperCase();
                        const allPrograms = deptProgramsMap[codeKey] || [
                          { code: "CS2034", name: "Computer Science & Engineering" },
                        ];

                        return (
                          <tr key={dept.id} className="hover:bg-[#f0f7ff] transition">
                            <td className="py-3.5 px-6 font-mono font-bold text-[#1473e6]">{dept.code}</td>
                            <td className="py-3.5 px-6">
                              <button
                                type="button"
                                onClick={() => setActiveDrilldownDept(dept)}
                                className="font-bold text-slate-900 hover:text-[#0c70d4] text-sm flex items-center gap-1.5 group transition"
                              >
                                <span>{dept.name}</span>
                                <span className="text-xs text-[#0c70d4] opacity-0 group-hover:opacity-100 transition-opacity">
                                  🔗 View Details
                                </span>
                              </button>
                            </td>

                            <td className="py-3.5 px-6">
                              <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded text-[11px] font-semibold">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Active
                              </span>
                            </td>

                            <td className="py-3.5 px-6 text-slate-600">
                              <div className="flex flex-col gap-1">
                                {allPrograms.map((p: any, idx: number) => (
                                  <span
                                    key={idx}
                                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#f7fbff] border border-cyan-100 text-slate-800 font-medium text-xs"
                                  >
                                    🎓 <strong className="text-[#1473e6] font-bold">{p.code}</strong> - {p.name}
                                  </span>
                                ))}
                              </div>
                            </td>

                            <td className="py-3.5 px-6 text-right">
                              <div className="flex justify-end gap-2">
                                <button
                                  type="button"
                                  onClick={() => openComprehensiveEdit(dept)}
                                  className="border border-amber-200 bg-amber-50/70 hover:bg-amber-100 text-amber-700 px-3 py-1 rounded-lg font-bold text-xs transition flex items-center gap-1"
                                >
                                  ✏️ Edit All
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteDepartment(dept.id, dept.name)}
                                  className="border border-rose-200 bg-rose-50/70 hover:bg-rose-100 text-rose-600 px-3 py-1 rounded-lg font-bold text-xs transition"
                                >
                                  🗑 Delete
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ===================== TAB 2: SETUP WITH AUTO CALENDAR DATES ===================== */}
      {activeTab === "create" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Card 1: Add Institute */}
          <div className="bg-white rounded-2xl p-6 border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] space-y-3">
            <div className="flex items-center gap-2 border-b border-cyan-100 pb-2">
              <span className="text-lg">🏫</span>
              <div>
                <h3 className="font-extrabold text-slate-900 text-sm">1. Add Institute</h3>
                <p className="text-[11px] text-slate-400">Root Node of Academic Hierarchy</p>
              </div>
            </div>
            <form onSubmit={submitInstitute} className="space-y-2.5">
              <div>
                <label className="text-xs font-bold text-slate-600">Institute Name *</label>
                <input
                  name="name"
                  placeholder="e.g. Finolex Academy"
                  required
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 outline-none focus:ring-2 focus:ring-cyan-400 bg-[#f7fbff]"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-600">State / Region *</label>
                <input
                  name="state"
                  placeholder="e.g. Maharashtra"
                  defaultValue="Maharashtra"
                  required
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 outline-none focus:ring-2 focus:ring-cyan-400 bg-[#f7fbff]"
                />
              </div>
              <button
                type="submit"
                className="w-full bg-gradient-to-r from-[#1d63ea] to-[#0295e6] hover:from-[#1554cd] hover:to-[#0284cc] text-white font-bold py-2.5 rounded-xl text-xs transition shadow-md shadow-blue-500/25"
              >
                + Add Institute
              </button>
            </form>
          </div>

          {/* Card 2: Add Department */}
          <div className="bg-white rounded-2xl p-6 border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] space-y-3">
            <div className="flex items-center gap-2 border-b border-cyan-100 pb-2">
              <span className="text-lg">🏢</span>
              <div>
                <h3 className="font-extrabold text-slate-900 text-sm">2. Add Department</h3>
                <p className="text-[11px] text-slate-400">Parent: {activeInst?.name || "Select Institute First"}</p>
              </div>
            </div>
            <form onSubmit={submitDepartment} className="space-y-2.5">
              <div className="grid grid-cols-3 gap-2">
                <div className="col-span-1">
                  <label className="text-xs font-bold text-slate-600">Dept Code *</label>
                  <input
                    name="code"
                    type="text"
                    pattern="^(?=.*[a-zA-Z])(?=.*[0-9])[a-zA-Z0-9_-]+$"
                    title="Alphanumeric code only"
                    placeholder="CSE2024"
                    required
                    disabled={!effectiveInstId}
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 uppercase outline-none focus:ring-2 focus:ring-cyan-400 bg-[#f7fbff] disabled:bg-slate-100"
                  />
                </div>
                <div className="col-span-2">
                  <label className="text-xs font-bold text-slate-600">Dept Name *</label>
                  <input
                    name="name"
                    placeholder="Computer Science"
                    required
                    disabled={!effectiveInstId}
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 outline-none focus:ring-2 focus:ring-cyan-400 bg-[#f7fbff] disabled:bg-slate-100"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={!effectiveInstId}
                className="w-full bg-gradient-to-r from-cyan-600 to-teal-500 hover:from-cyan-700 hover:to-teal-600 text-white font-bold py-2.5 rounded-xl text-xs transition shadow-md shadow-cyan-500/25 disabled:opacity-50"
              >
                + Add Department
              </button>
            </form>
          </div>

          {/* Card 3: Class Year & Calendar Sync */}
          <div className="bg-white rounded-2xl p-6 border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] space-y-3">
            <div className="flex items-center gap-2 border-b border-cyan-100 pb-2">
              <span className="text-lg">⏳</span>
              <div>
                <h3 className="font-extrabold text-slate-900 text-sm">3. Class Term & Calendar Sync</h3>
                <p className="text-[11px] text-slate-400">Respective Dates Auto-Extracted</p>
              </div>
            </div>
            <div className="space-y-2.5">
              <div>
                <label className="text-xs font-bold text-slate-600">Class Level</label>
                <select
                  value={selectedClassLevel}
                  onChange={(e) => setSelectedClassLevel(e.target.value as any)}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 outline-none bg-[#f7fbff] font-bold text-[#0c70d4]"
                >
                  <option value="FE">FE (First Year - Sem 1 & 2)</option>
                  <option value="SE">SE (Second Year - Sem 3 & 4)</option>
                  <option value="TE">TE (Third Year - Sem 5 & 6)</option>
                  <option value="BE">BE (Final Year - Sem 7 & 8)</option>
                </select>
              </div>

              <div className="bg-[#f7fbff] border border-cyan-100 rounded-xl p-3 space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500 font-medium">Respective Start Date:</span>
                  <span className="font-mono font-bold text-[#1473e6]">{autoDates.start}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500 font-medium">Respective End Date:</span>
                  <span className="font-mono font-bold text-rose-600">{autoDates.end}</span>
                </div>
                <span className="text-[10px] text-slate-400 italic block mt-1">
                  ✓ Sourced from uploaded academic calendar PDF
                </span>
              </div>

              <button
                type="button"
                onClick={submitSemesterWithAutoDates}
                className="w-full bg-gradient-to-r from-[#1d63ea] to-[#0295e6] hover:from-[#1554cd] hover:to-[#0284cc] text-white font-bold py-2.5 rounded-xl text-xs transition shadow-md shadow-blue-500/25"
              >
                Apply Respective Dates
              </button>
            </div>
          </div>

          {/* Card 6: Add Class & Capacity (FE, SE, TE, BE) */}
          <div className="bg-white rounded-2xl p-6 border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] space-y-3 col-span-1 md:col-span-2 lg:col-span-3">
            <div className="flex items-center gap-2 border-b border-cyan-100 pb-2">
              <span className="text-lg">👥</span>
              <div>
                <h3 className="font-extrabold text-slate-900 text-sm">4. Configure Class & Capacity (FE, SE, TE, BE)</h3>
                <p className="text-[11px] text-slate-400">
                  Target Department: {departmentList.find((d) => d.id === departmentId)?.name || departmentList[0]?.name || "Select Department"}
                </p>
              </div>
            </div>

            <form onSubmit={submitAddClassCapacity} className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
              <div>
                <label className="text-xs font-bold text-slate-600">Select Class Level *</label>
                <select
                  value={newClassInput.className}
                  onChange={(e) =>
                    setNewClassInput({ ...newClassInput, className: e.target.value as any })
                  }
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 outline-none bg-[#f7fbff] font-bold text-[#0c70d4]"
                >
                  <option value="FE">FE (First Year)</option>
                  <option value="SE">SE (Second Year)</option>
                  <option value="TE">TE (Third Year)</option>
                  <option value="BE">BE (Final Year)</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600">Intake Capacity (Seats) *</label>
                <input
                  type="number"
                  min={1}
                  required
                  value={newClassInput.capacity}
                  onChange={(e) =>
                    setNewClassInput({ ...newClassInput, capacity: Number(e.target.value) || 60 })
                  }
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 outline-none bg-[#f7fbff] font-bold text-slate-900"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-gradient-to-r from-[#1d63ea] to-[#0295e6] hover:from-[#1554cd] hover:to-[#0284cc] text-white font-bold py-2.5 rounded-xl text-xs transition shadow-md shadow-blue-500/25"
              >
                + Save Class & Capacity
              </button>
            </form>
          </div>
        </div>
      )}

      {/* ===================== COMPREHENSIVE EDIT MODAL (CLASS & INTAKE CAPACITY) ===================== */}
      {comprehensiveEdit && (
        <div className="fixed inset-0 bg-[#07193b]/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 border border-cyan-100 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3 mb-4">
              <h3 className="text-base font-extrabold text-slate-900">Edit Complete Academic Hierarchy Details</h3>
              <button
                type="button"
                onClick={() => setComprehensiveEdit(null)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveComprehensiveEdit} className="space-y-4">
              {/* Department Info */}
              <div className="p-3 bg-[#f7fbff] rounded-xl border border-cyan-100 space-y-2">
                <span className="text-xs font-black text-[#0c70d4] uppercase">DEPARTMENT INFO</span>
                <div className="grid grid-cols-3 gap-2">
                  <input
                    type="text"
                    required
                    value={comprehensiveEdit.deptCode}
                    onChange={(e) => setComprehensiveEdit({ ...comprehensiveEdit, deptCode: e.target.value })}
                    className="border border-cyan-200 rounded-xl p-2.5 text-xs uppercase font-bold"
                  />
                  <input
                    type="text"
                    required
                    value={comprehensiveEdit.deptName}
                    onChange={(e) => setComprehensiveEdit({ ...comprehensiveEdit, deptName: e.target.value })}
                    className="col-span-2 border border-cyan-200 rounded-xl p-2.5 text-xs font-semibold"
                  />
                </div>
              </div>

              {/* CLASS & INTAKE CAPACITY (Replaced Section) */}
              <div className="p-3 bg-[#f7fbff] rounded-xl border border-cyan-100 space-y-2">
                <span className="text-xs font-black text-[#0c70d4] uppercase">CLASS & INTAKE CAPACITY</span>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Class (FE / SE / TE / BE)</label>
                    <select
                      value={comprehensiveEdit.className}
                      onChange={(e) =>
                        setComprehensiveEdit({
                          ...comprehensiveEdit,
                          className: e.target.value as "FE" | "SE" | "TE" | "BE",
                        })
                      }
                      className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-[#0c70d4] bg-white outline-none"
                    >
                      <option value="FE">Class FE (First Year)</option>
                      <option value="SE">Class SE (Second Year)</option>
                      <option value="TE">Class TE (Third Year)</option>
                      <option value="BE">Class BE (Final Year)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Capacity (Total Seats)</label>
                    <input
                      type="number"
                      min={1}
                      required
                      value={comprehensiveEdit.capacity}
                      onChange={(e) => setComprehensiveEdit({ ...comprehensiveEdit, capacity: Number(e.target.value) || 60 })}
                      className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold bg-white outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setComprehensiveEdit(null)}
                  className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white rounded-xl text-xs font-bold hover:from-[#1554cd] hover:to-[#0284cc] shadow-md shadow-blue-500/25"
                >
                  Save All Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Rename Institute Modal */}
      {editInstModal && (
        <div className="fixed inset-0 bg-[#07193b]/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-5 border border-cyan-100">
            <h3 className="text-sm font-extrabold text-slate-800 mb-3">Rename Institute</h3>
            <input
              type="text"
              value={editInstModal.name}
              onChange={(e) => setEditInstModal({ ...editInstModal, name: e.target.value })}
              className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs outline-none bg-[#f7fbff]"
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                type="button"
                onClick={() => setEditInstModal(null)}
                className="px-3.5 py-1.5 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  notify.success("Institute renamed.");
                  setEditInstModal(null);
                }}
                className="px-3.5 py-1.5 bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/25"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}