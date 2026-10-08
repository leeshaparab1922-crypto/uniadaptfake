import React, { useState, useEffect } from "react";

interface Student {
  roll_number: string;
  full_name: string;
  email: string;
  current_semester_no?: number;
  semester?: number;
  class_tier?: "FE" | "SE" | "TE" | "BE";
  department_code?: string;
  program_code?: string;
  batch_start_year?: number;
  status?: string;
  source_file?: string;
  institute_id?: string;
}

interface UploadHistoryItem {
  file_name: string;
  upload_date: string;
  students_count: number;
  department_code: string;
  class_tier: "FE" | "SE" | "TE" | "BE";
  institute_id: string;
}

interface ClassRecordItem {
  id: string;
  deptCode: string;
  batchName: string;
  className: "FE" | "SE" | "TE" | "BE";
  semesterNo: number;
  startDate: string;
  endDate: string;
  capacity: number;
}

export const StudentImport: React.FC = () => {
  const currentInstituteId = localStorage.getItem("uniadapt_active_institute_id") || "inst_famt_01";
  const currentInstituteName = localStorage.getItem("uniadapt_active_institute_name") || "finolex";

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
      { code: "CSE2024", name: "Computer Science (CSE2024)" },
      { code: "CSE2005", name: "Computer Science Engineering (CSE2005)" },
      { code: "CSL102", name: "cse" },
      { code: "IT2004", name: "Information Technology (IT2004)" },
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

  // 2. Track live hierarchy classes for capacity verification
  const [hierarchyClasses, setHierarchyClasses] = useState<ClassRecordItem[]>([]);

  const refreshHierarchyClasses = () => {
    const cached = localStorage.getItem("uniadapt_dept_classes_clean");
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setHierarchyClasses(parsed);
          return;
        }
      } catch (e) {
        console.error(e);
      }
    }

    const oldCached = localStorage.getItem("uniadapt_dept_classes_data");
    if (oldCached) {
      try {
        const parsedOld = JSON.parse(oldCached);
        if (Array.isArray(parsedOld)) {
          setHierarchyClasses(parsedOld);
          return;
        }
      } catch (e) {
        console.error(e);
      }
    }
  };

  useEffect(() => {
    refreshHierarchyClasses();
    window.addEventListener("storage", refreshHierarchyClasses);
    return () => window.removeEventListener("storage", refreshHierarchyClasses);
  }, []);

  // Upload Form Selection States
  const [uploadDept, setUploadDept] = useState<string>(departments[0]?.code || "CSE2005");
  const availableUploadClasses = hierarchyClasses.filter((c) => c.deptCode === uploadDept);
  const [uploadClass, setUploadClass] = useState<"FE" | "SE" | "TE" | "BE">(
    (availableUploadClasses[0]?.className as any) || "SE"
  );

  useEffect(() => {
    if (departments.length > 0 && !departments.some((d) => d.code === uploadDept)) {
      setUploadDept(departments[0].code);
    }
  }, [departments]);

  useEffect(() => {
    const matched = hierarchyClasses.filter((c) => c.deptCode === uploadDept);
    if (matched.length > 0) {
      setUploadClass(matched[0].className);
    } else {
      setUploadClass("SE");
    }
  }, [uploadDept, hierarchyClasses]);

  // View Uploaded CSV Dropdown Filter
  const [viewHistoryDept, setViewHistoryDept] = useState<string>("ALL");

  // Filter for View Batch in Student Table (NULL MEANS TABLE IS CLOSED / HIDDEN)
  const [selectedBatchFilter, setSelectedBatchFilter] = useState<string | null>(null);

  // Storage: Students
  const [allStudents, setAllStudents] = useState<Student[]>(() => {
    const cached = localStorage.getItem("uniadapt_imported_students_cache");
    return cached
      ? JSON.parse(cached)
      : [
          {
            roll_number: "CSESE3001",
            full_name: "Aarav Patil",
            email: "aarav.patil@example.com",
            current_semester_no: 3,
            class_tier: "SE",
            department_code: "CSE2005",
            status: "Enrolled",
            source_file: "SE Student.csv",
            institute_id: currentInstituteId,
          },
          {
            roll_number: "CSESE3002",
            full_name: "Ananya Jadhav",
            email: "ananya.jadhav@example.com",
            current_semester_no: 3,
            class_tier: "SE",
            department_code: "CSE2005",
            status: "Enrolled",
            source_file: "SE Student.csv",
            institute_id: currentInstituteId,
          },
        ];
  });

  // Storage: Upload History
  const [allHistory, setAllHistory] = useState<UploadHistoryItem[]>(() => {
    const cached = localStorage.getItem("uniadapt_upload_history_cache");
    return cached
      ? JSON.parse(cached)
      : [
          {
            file_name: "SE Student.csv",
            upload_date: "4/10/2026, 11:07:59 pm",
            students_count: 61,
            department_code: "CSE2005",
            class_tier: "SE",
            institute_id: currentInstituteId,
          },
        ];
  });

  // Component UI States
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Modals States
  const [editingStudent, setEditingStudent] = useState<Student | null>(null);

  // Sync to Storage
  useEffect(() => {
    localStorage.setItem("uniadapt_imported_students_cache", JSON.stringify(allStudents));
  }, [allStudents]);

  useEffect(() => {
    localStorage.setItem("uniadapt_upload_history_cache", JSON.stringify(allHistory));
  }, [allHistory]);

  // Dynamic capacity resolution from live hierarchy records
  const getActiveCapacityLimit = (dept: string, tier: string): number => {
    const matched = hierarchyClasses.find(
      (c) => c.deptCode === dept && c.className === tier
    );
    if (matched && matched.capacity) {
      return Number(matched.capacity);
    }

    const cached = localStorage.getItem("uniadapt_dept_classes_clean");
    if (cached) {
      try {
        const parsed: ClassRecordItem[] = JSON.parse(cached);
        const found = parsed.find((c) => c.deptCode === dept && c.className === tier);
        if (found && found.capacity) {
          return Number(found.capacity);
        }
      } catch (e) {
        console.error(e);
      }
    }

    const anyClassInDept = hierarchyClasses.find((c) => c.deptCode === dept);
    if (anyClassInDept && anyClassInDept.capacity) {
      return Number(anyClassInDept.capacity);
    }

    return 70;
  };

  const currentCapacityLimit = getActiveCapacityLimit(uploadDept, uploadClass);
  const enrolledCountForSelectedClass = allStudents.filter(
    (s) => s.department_code === uploadDept && (s.class_tier || "SE") === uploadClass
  ).length;

  const sortStudentsByRoll = (list: Student[]): Student[] => {
    return [...list].sort((a, b) =>
      a.roll_number.localeCompare(b.roll_number, undefined, { numeric: true, sensitivity: "base" })
    );
  };

  // 1. Download Sample CSV
  const handleDownloadSampleCsv = () => {
    const sampleContent =
      "roll_number,full_name,email,department_code,current_semester_no,class_tier\n" +
      `STU3001,Aarav Patil,aarav.patil@example.com,${uploadDept},3,${uploadClass}\n` +
      `STU3002,Ananya Jadhav,ananya.jadhav@example.com,${uploadDept},3,${uploadClass}`;

    const blob = new Blob([sampleContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `sample_student_import_${uploadDept}_${uploadClass}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setSuccessBanner("Sample CSV template downloaded successfully!");
    setTimeout(() => setSuccessBanner(null), 3000);
  };

  // 2. Export Students CSV
  const handleExportStudents = () => {
    const exportData = selectedBatchFilter
      ? allStudents.filter((s) => s.source_file === selectedBatchFilter)
      : allStudents;

    if (exportData.length === 0) {
      alert("No students available to export!");
      return;
    }

    const headers = "roll_number,full_name,email,department,class,semester,status\n";
    const rows = exportData
      .map(
        (s) =>
          `"${s.roll_number}","${s.full_name}","${s.email}","${s.department_code || uploadDept}","${s.class_tier || "SE"}","Sem ${s.current_semester_no || 3}","${s.status || "Enrolled"}"`
      )
      .join("\n");

    const blob = new Blob([headers + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `${(selectedBatchFilter || "all_enrolled").replace(/\s+/g, "_")}_students.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setSuccessBanner(`Exported ${exportData.length} student records.`);
    setTimeout(() => setSuccessBanner(null), 3000);
  };

  // 3. Import CSV with Real Capacity Check
  const handleImportCsv = async () => {
    if (!selectedFile) {
      alert("Please choose a CSV file first.");
      return;
    }

    if (allHistory.some((h) => h.file_name.toLowerCase() === selectedFile.name.toLowerCase())) {
      setErrorMessage(`File "${selectedFile.name}" is already uploaded!`);
      return;
    }

    const effectiveCapacity = getActiveCapacityLimit(uploadDept, uploadClass);

    const text = await selectedFile.text();
    const rows = text.split("\n").filter((r) => r.trim() !== "");
    const incomingStudents: Student[] = rows.slice(1).map((row) => {
      const cols = row.split(",");
      return {
        roll_number: cols[0]?.trim() || `STU${Date.now()}`,
        full_name: cols[1]?.trim() || "Student",
        email: cols[2]?.trim() || "",
        department_code: uploadDept,
        current_semester_no: Number(cols[4]) || 3,
        class_tier: uploadClass,
        status: "Enrolled",
        source_file: selectedFile.name,
        institute_id: currentInstituteId,
      };
    });

    const currentClassCount = allStudents.filter(
      (s) => s.department_code === uploadDept && (s.class_tier || "SE") === uploadClass
    ).length;

    const projectedTotal = currentClassCount + incomingStudents.length;

    if (projectedTotal > effectiveCapacity) {
      const excess = projectedTotal - effectiveCapacity;
      setErrorMessage(
        `Capacity Limit Exceeded for ${uploadDept} (${uploadClass})! Configured capacity in Hierarchy is ${effectiveCapacity} seats. Currently filled: ${currentClassCount}. Trying to add: ${incomingStudents.length} (${excess} seats over capacity).`
      );
      return;
    }

    setAllStudents([...allStudents, ...incomingStudents]);
    setAllHistory([
      {
        file_name: selectedFile.name,
        upload_date: new Date().toLocaleString(),
        students_count: incomingStudents.length,
        department_code: uploadDept,
        class_tier: uploadClass,
        institute_id: currentInstituteId,
      },
      ...allHistory,
    ]);

    setSuccessBanner(
      `File "${selectedFile.name}" uploaded successfully for ${uploadDept} (${uploadClass}). Current Intake: ${projectedTotal}/${effectiveCapacity} seats filled.`
    );
    // Automatically view the newly uploaded file in table
    setSelectedBatchFilter(selectedFile.name);
    setSelectedFile(null);
    setErrorMessage(null);
    setTimeout(() => setSuccessBanner(null), 4000);
  };

  // 4. Delete Student
  const handleDeleteStudent = (rollNo: string) => {
    if (window.confirm(`Are you sure you want to delete student ${rollNo}?`)) {
      setAllStudents(allStudents.filter((s) => s.roll_number !== rollNo));
      setSuccessBanner(`Student ${rollNo} deleted.`);
      setTimeout(() => setSuccessBanner(null), 3000);
    }
  };

  // 5. Delete Entire Batch File
  const handleDeleteBatchFile = (fileName: string) => {
    if (window.confirm(`Delete batch file "${fileName}"? All students belonging to this file will be removed.`)) {
      setAllHistory(allHistory.filter((h) => h.file_name !== fileName));
      setAllStudents(allStudents.filter((s) => s.source_file !== fileName));
      if (selectedBatchFilter === fileName) {
        setSelectedBatchFilter(null);
      }
      setSuccessBanner(`Batch file "${fileName}" and its student records were removed.`);
      setTimeout(() => setSuccessBanner(null), 3500);
    }
  };

  // 6. Edit Student Submit
  const handleEditStudentSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingStudent) return;

    setAllStudents(
      allStudents.map((s) => (s.roll_number === editingStudent.roll_number ? editingStudent : s))
    );
    setSuccessBanner(`Details updated for ${editingStudent.roll_number}.`);
    setEditingStudent(null);
    setTimeout(() => setSuccessBanner(null), 3000);
  };

  // Filtered History according to Department Dropdown
  const filteredHistory =
    viewHistoryDept === "ALL"
      ? allHistory
      : allHistory.filter((h) => h.department_code === viewHistoryDept);

  // STRICT FILE-WISE FILTERING: ONLY SHOW STUDENTS IF A FILE IS EXPLICITLY VIEWED!
  const baseStudents = selectedBatchFilter
    ? allStudents.filter((s) => s.source_file === selectedBatchFilter)
    : [];

  const filteredStudents = sortStudentsByRoll(
    baseStudents.filter(
      (s) =>
        (s.full_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
        (s.roll_number || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
        (s.email || "").toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  const totalPages = Math.ceil(filteredStudents.length / rowsPerPage) || 1;
  const paginatedStudents = filteredStudents.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);

  return (
    <div className="min-h-screen bg-[#eaf4fe] p-4 sm:p-6 lg:p-8 space-y-6 font-sans text-slate-800">
      {/* NOTIFICATION BANNERS */}
      {successBanner && (
        <div className="bg-emerald-600 text-white p-3.5 rounded-2xl shadow-lg flex justify-between items-center text-xs font-bold animate-fadeIn">
          <span>✅ {successBanner}</span>
          <button onClick={() => setSuccessBanner(null)} className="font-black text-sm ml-2">
            ✕
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="bg-rose-50 border border-rose-300 text-rose-800 p-3.5 rounded-2xl shadow-lg flex justify-between items-center text-xs font-bold animate-fadeIn">
          <span>⚠️ {errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="font-black text-sm ml-2">
            ✕
          </button>
        </div>
      )}

      {/* 1. HERO BRAND BANNER */}
      <div className="relative overflow-hidden rounded-[24px] bg-gradient-to-r from-[#07193b] via-[#09295e] to-[#04122d] border border-cyan-400/40 p-6 sm:p-7 shadow-xl shadow-blue-950/20">
        <div className="absolute -top-16 -right-16 w-80 h-80 bg-cyan-400/20 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="bg-[#0e3b79] text-cyan-300 border border-cyan-400/40 text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                ENROLLMENT MODULE
              </span>
              <span className="text-cyan-300 text-xs font-bold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                {currentInstituteName}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
              Student CSV Import & Records
            </h1>
            <p className="text-xs sm:text-sm text-cyan-100/80 mt-0.5">
              Upload bulk batches, view specific files department-wise, and manage class enrollments.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleDownloadSampleCsv}
              className="px-4 py-2 border border-cyan-400/50 rounded-xl text-xs font-bold text-white bg-blue-900/60 hover:bg-blue-800 transition flex items-center gap-1.5 shadow-sm"
            >
              📥 Download Sample CSV
            </button>
            <button
              onClick={handleExportStudents}
              className="px-4 py-2 border border-cyan-400/50 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-[#1d63ea] to-[#0295e6] hover:from-[#1554cd] hover:to-[#0284cc] transition flex items-center gap-1.5 shadow-md shadow-blue-500/20"
            >
              📤 Export Students
            </button>
          </div>
        </div>
      </div>

      {/* 2. UPLOAD STUDENT CSV CARD */}
      <div className="bg-white rounded-2xl p-6 border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] space-y-4">
        <div className="flex flex-wrap justify-between items-center gap-3 border-b border-cyan-50 pb-3">
          <div>
            <h3 className="font-extrabold text-slate-900 text-sm">Upload Student CSV</h3>
            <p className="text-[11px] text-slate-500">
              Select department and target class to enforce capacity verification configured in Hierarchy
            </p>
          </div>
          <div className="bg-[#f0f7ff] border border-cyan-200 px-3.5 py-1.5 rounded-xl flex items-center gap-3">
            <span className="text-xs font-bold text-slate-600">
              Configured Capacity for {uploadDept} ({uploadClass}):
            </span>
            <span
              className={`text-xs font-black ${
                enrolledCountForSelectedClass >= currentCapacityLimit
                  ? "text-rose-600"
                  : "text-emerald-600"
              }`}
            >
              {enrolledCountForSelectedClass} / {currentCapacityLimit} Seats Filled
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          {/* Select Department */}
          <div>
            <label className="text-[11px] font-bold text-slate-600 uppercase block mb-1">
              Select Department *
            </label>
            <select
              value={uploadDept}
              onChange={(e) => setUploadDept(e.target.value)}
              className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-bold text-slate-900 bg-[#f7fbff] outline-none focus:ring-2 focus:ring-cyan-400"
            >
              {departments.map((d) => (
                <option key={d.code} value={d.code}>
                  {d.name} ({d.code})
                </option>
              ))}
            </select>
          </div>

          {/* Select Class */}
          <div>
            <label className="text-[11px] font-bold text-slate-600 uppercase block mb-1">
              Select Class Year *
            </label>
            <select
              value={uploadClass}
              onChange={(e) => setUploadClass(e.target.value as any)}
              className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs font-black text-[#0c70d4] bg-[#f7fbff] outline-none focus:ring-2 focus:ring-cyan-400"
            >
              <option value="FE">FE (First Year)</option>
              <option value="SE">SE (Second Year)</option>
              <option value="TE">TE (Third Year)</option>
              <option value="BE">BE (Final Year)</option>
            </select>
          </div>

          {/* Choose File */}
          <div>
            <label className="text-[11px] font-bold text-slate-600 uppercase block mb-1">
              Select CSV File *
            </label>
            <input
              type="file"
              accept=".csv"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setSelectedFile(e.target.files[0]);
                  setErrorMessage(null);
                }
              }}
              className="w-full border border-cyan-200 rounded-xl p-1.5 text-xs text-slate-600 bg-white file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-bold file:bg-blue-50 file:text-blue-700"
            />
          </div>

          {/* Import Button */}
          <div>
            <button
              onClick={handleImportCsv}
              disabled={enrolledCountForSelectedClass >= currentCapacityLimit}
              className="w-full bg-gradient-to-r from-[#1d63ea] to-[#0295e6] hover:from-[#1554cd] hover:to-[#0284cc] text-white font-bold py-2.5 rounded-xl text-xs transition shadow-md shadow-blue-500/25 disabled:opacity-50"
            >
              + Import CSV ({currentCapacityLimit} Seats Cap)
            </button>
          </div>
        </div>
      </div>

      {/* 3. VIEW UPLOADED STUDENT CSV FILES (DEPARTMENT FILTER) */}
      <div className="bg-white rounded-2xl border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] overflow-hidden space-y-3">
        <div className="p-5 border-b border-cyan-50 flex flex-wrap justify-between items-center gap-3 bg-[#f7fbff]">
          <div>
            <h3 className="text-sm font-extrabold text-slate-900">View Uploaded Student CSV Files</h3>
            <p className="text-xs text-slate-500 mt-0.5">Click "View File" on any specific batch to view its students below</p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-600">Filter Department:</span>
            <select
              value={viewHistoryDept}
              onChange={(e) => setViewHistoryDept(e.target.value)}
              className="border border-cyan-200 rounded-xl px-3 py-1.5 text-xs font-bold text-[#0c70d4] bg-white outline-none focus:ring-2 focus:ring-cyan-400 shadow-2xs"
            >
              <option value="ALL">All Departments ({allHistory.length})</option>
              {departments.map((d) => (
                <option key={d.code} value={d.code}>
                  {d.name} ({d.code})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-50 text-slate-600 font-black border-b border-slate-100 uppercase tracking-wider text-[10px]">
                <th className="py-3.5 px-6">FILE NAME</th>
                <th className="py-3.5 px-6">DEPARTMENT</th>
                <th className="py-3.5 px-6">CLASS TIER</th>
                <th className="py-3.5 px-6">UPLOAD DATE & TIME</th>
                <th className="py-3.5 px-6">STUDENTS IMPORTED</th>
                <th className="py-3.5 px-6 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredHistory.map((h, idx) => {
                const isActiveInTable = selectedBatchFilter === h.file_name;
                return (
                  <tr key={idx} className={`transition ${isActiveInTable ? "bg-blue-50/70" : "hover:bg-[#f0f7ff]"}`}>
                    <td className="py-3.5 px-6 font-bold text-slate-900 flex items-center gap-2">
                      📄 {h.file_name}
                      {isActiveInTable && (
                        <span className="text-[10px] bg-blue-600 text-white px-2 py-0.5 rounded-full font-bold">
                          Active In Table
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-6 font-mono font-bold text-[#1473e6]">
                      {h.department_code || uploadDept}
                    </td>
                    <td className="py-3.5 px-6 font-bold text-indigo-700">
                      <span className="bg-indigo-50 border border-indigo-200 px-2.5 py-0.5 rounded-md">
                        {h.class_tier || "SE"}
                      </span>
                    </td>
                    <td className="py-3.5 px-6 text-slate-500 font-medium">{h.upload_date}</td>
                    <td className="py-3.5 px-6">
                      <span className="bg-emerald-50 text-emerald-800 border border-emerald-200 px-2.5 py-0.5 rounded-full font-bold text-xs inline-flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        {h.students_count} Students
                      </span>
                    </td>
                    <td className="py-3.5 px-6 text-right">
                      <div className="flex justify-end gap-2">
                        {/* TOGGLE VIEW CSV IN TABLE BUTTON */}
                        <button
                          type="button"
                          onClick={() => {
                            if (selectedBatchFilter === h.file_name) {
                              setSelectedBatchFilter(null);
                            } else {
                              setSelectedBatchFilter(h.file_name);
                              setCurrentPage(1);
                            }
                          }}
                          className={`px-3 py-1 rounded-lg text-xs font-bold transition flex items-center gap-1 ${
                            isActiveInTable
                              ? "bg-blue-600 text-white shadow-sm"
                              : "border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100"
                          }`}
                        >
                          {isActiveInTable ? "✕ Close View" : "👁 View File"}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteBatchFile(h.file_name)}
                          className="border border-rose-200 bg-rose-50/70 hover:bg-rose-100 text-rose-600 px-3 py-1 rounded-lg text-xs font-bold transition flex items-center gap-1"
                        >
                          🗑 Delete Batch
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}

              {filteredHistory.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400 font-medium">
                    No uploaded CSV files found for {viewHistoryDept === "ALL" ? "any department" : viewHistoryDept}.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 4. ENROLLED STUDENTS RECORDS TABLE (DISPLAYS ONLY WHEN A FILE IS VIEWED!) */}
      {/* ========================================================================= */}
      {selectedBatchFilter ? (
        <div className="bg-white rounded-2xl border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] p-6 space-y-4 animate-fadeIn">
          <div className="flex flex-wrap justify-between items-center gap-3 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h2 className="text-base font-extrabold text-slate-900">
                Viewing File: <span className="text-[#0c70d4]">{selectedBatchFilter}</span> ({filteredStudents.length} Students)
              </h2>
              {/* Top Close Table Button */}
              <button
                onClick={() => setSelectedBatchFilter(null)}
                className="bg-rose-50 border border-rose-200 text-rose-700 hover:bg-rose-100 px-3 py-1 rounded-xl text-xs font-bold transition flex items-center gap-1"
              >
                ✕ Close File View
              </button>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="text"
                placeholder="Search by name, roll no, email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="border border-cyan-200 rounded-xl px-3 py-1.5 text-xs w-60 outline-none focus:ring-2 focus:ring-cyan-400 font-medium bg-[#f7fbff]"
              />
              <select
                value={rowsPerPage}
                onChange={(e) => setRowsPerPage(Number(e.target.value))}
                className="border border-cyan-200 rounded-xl px-2.5 py-1.5 text-xs text-slate-600 bg-white font-bold"
              >
                <option value={10}>10 / page</option>
                <option value={20}>20 / page</option>
                <option value={50}>50 / page</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-600 font-black border-b border-slate-100 uppercase tracking-wider text-[10px]">
                  <th className="py-3 px-4">ROLL #</th>
                  <th className="py-3 px-4">NAME</th>
                  <th className="py-3 px-4">EMAIL</th>
                  <th className="py-3 px-4">DEPARTMENT</th>
                  <th className="py-3 px-4">CLASS</th>
                  <th className="py-3 px-4">SEMESTER</th>
                  <th className="py-3 px-4">STATUS</th>
                  <th className="py-3 px-4 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginatedStudents.map((st) => (
                  <tr key={st.roll_number} className="hover:bg-[#f0f7ff] transition">
                    <td className="py-3 px-4 font-bold text-slate-900">{st.roll_number}</td>
                    <td className="py-3 px-4 font-bold text-slate-800">{st.full_name}</td>
                    <td className="py-3 px-4 text-slate-500 font-medium">{st.email}</td>
                    <td className="py-3 px-4 font-mono font-bold text-[#1473e6]">
                      {st.department_code || uploadDept}
                    </td>
                    <td className="py-3 px-4 font-bold text-indigo-700">
                      <span className="bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded">
                        {st.class_tier || "SE"}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-600 font-semibold">
                      Sem {st.current_semester_no || 3}
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full font-bold text-[11px]">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Enrolled
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => setEditingStudent(st)}
                          className="border border-amber-200 bg-amber-50/70 hover:bg-amber-100 text-amber-700 px-2.5 py-1 rounded-lg text-xs font-bold transition"
                        >
                          ✏️ Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteStudent(st.roll_number)}
                          className="border border-rose-200 bg-rose-50/70 hover:bg-rose-100 text-rose-600 px-2.5 py-1 rounded-lg text-xs font-bold transition"
                        >
                          🗑 Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}

                {paginatedStudents.length === 0 && (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-400 font-medium">
                      No student records found in this file.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="flex justify-between items-center text-xs text-slate-500 pt-3 border-t border-slate-100">
            <span>
              Showing page {currentPage} of {totalPages}
            </span>
            <div className="flex gap-1.5">
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                className="px-3 py-1 border border-cyan-200 rounded-lg disabled:opacity-40 font-bold hover:bg-blue-50"
              >
                Previous
              </button>
              <button
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                className="px-3 py-1 border border-cyan-200 rounded-lg disabled:opacity-40 font-bold hover:bg-blue-50"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {/* 5. EDIT STUDENT MODAL */}
      {editingStudent && (
        <div className="fixed inset-0 bg-[#07193b]/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-cyan-100">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3 mb-4">
              <h3 className="text-base font-extrabold text-slate-900">Edit Student Details</h3>
              <button
                type="button"
                onClick={() => setEditingStudent(null)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleEditStudentSubmit} className="space-y-3.5">
              <div>
                <label className="text-[11px] font-bold text-slate-600 uppercase">Roll Number (Read-Only)</label>
                <input
                  type="text"
                  disabled
                  value={editingStudent.roll_number}
                  className="w-full border bg-slate-100 rounded-xl p-2.5 text-xs mt-1 cursor-not-allowed font-bold text-slate-500"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-600 uppercase">Full Name *</label>
                <input
                  type="text"
                  required
                  value={editingStudent.full_name}
                  onChange={(e) => setEditingStudent({ ...editingStudent, full_name: e.target.value })}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-bold text-slate-900 outline-none focus:ring-2 focus:ring-cyan-400"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-600 uppercase">Email Address *</label>
                <input
                  type="email"
                  required
                  value={editingStudent.email}
                  onChange={(e) => setEditingStudent({ ...editingStudent, email: e.target.value })}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-medium text-slate-900 outline-none focus:ring-2 focus:ring-cyan-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-bold text-slate-600 uppercase">Class Year *</label>
                  <select
                    value={editingStudent.class_tier || "SE"}
                    onChange={(e) =>
                      setEditingStudent({ ...editingStudent, class_tier: e.target.value as any })
                    }
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-bold text-indigo-700 bg-white"
                  >
                    <option value="FE">FE</option>
                    <option value="SE">SE</option>
                    <option value="TE">TE</option>
                    <option value="BE">BE</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-600 uppercase">Semester</label>
                  <input
                    type="number"
                    min={1}
                    max={8}
                    value={editingStudent.current_semester_no || 3}
                    onChange={(e) =>
                      setEditingStudent({
                        ...editingStudent,
                        current_semester_no: Number(e.target.value),
                      })
                    }
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-bold text-slate-900"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setEditingStudent(null)}
                  className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-gradient-to-r from-[#1d63ea] to-[#0295e6] text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/25"
                >
                  Update Student
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentImport;