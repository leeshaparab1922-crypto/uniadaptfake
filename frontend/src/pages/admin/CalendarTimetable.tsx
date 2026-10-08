import React, { useState, useEffect } from 'react';

export interface CalendarMilestone {
  id: string;
  dateRange: string;
  activity: string;
  category: 'Teaching' | 'Exam' | 'Attendance' | 'Holiday' | 'Meeting' | 'Review';
  applicableClass: 'SE, TE, BE' | 'FE Sem 1' | 'All Classes' | 'College Wide';
}

export const CalendarTimetable: React.FC = () => {
  const currentInstituteId = localStorage.getItem('uniadapt_active_institute_id') || 'inst-1';
  const currentInstituteName =
    localStorage.getItem('uniadapt_active_institute_name') || 'Finolex Academy of Management & Technology';

  // Smart Date Parsing Helper for Sorting
  const parseDateForSort = (dateStr: string): number => {
    if (!dateStr) return 0;
    const cleanFirstPart = dateStr.split(/to|-/i)[0].trim();
    const parts = cleanFirstPart.split(/[/.-]/);
    if (parts.length < 3) return 0;
    const day = parseInt(parts[0], 10) || 1;
    const monthRaw = parts[1].toLowerCase();
    let year = parseInt(parts[2], 10) || 2026;
    if (year < 100) year += 2000;

    const monthMap: Record<string, number> = {
      jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
      jul: 6, aug: 7, sep: 8, sept: 8, oct: 9, nov: 10, dec: 11,
      '01': 0, '02': 1, '03': 2, '04': 3, '05': 4, '06': 5,
      '07': 6, '08': 7, '09': 8, '1': 0, '2': 1, '3': 2,
      '4': 3, '5': 4, '6': 5, '7': 6, '8': 7, '9': 8,
      '10': 9, '11': 10, '12': 11
    };

    const month = monthMap[monthRaw] !== undefined ? monthMap[monthRaw] : 0;
    return new Date(year, month, day).getTime();
  };

  const sortChronologically = (list: CalendarMilestone[]): CalendarMilestone[] => {
    return [...list].sort((a, b) => parseDateForSort(a.dateRange) - parseDateForSort(b.dateRange));
  };

  // State strictly stored per institute
  const [milestones, setMilestones] = useState<CalendarMilestone[]>(() => {
    const cached = localStorage.getItem(`uniadapt_academic_calendar_${currentInstituteId}`);
    if (cached) {
      try {
        return sortChronologically(JSON.parse(cached));
      } catch (e) {
        return [];
      }
    }
    return [];
  });

  const [sourcePdfName, setSourcePdfName] = useState<string>(() => {
    return localStorage.getItem(`uniadapt_calendar_source_${currentInstituteId}`) || '';
  });

  const [termDates, setTermDates] = useState<{
    seTeBe: { start: string; end: string };
    fe: { start: string; end: string };
  }>(() => {
    const cachedSE = localStorage.getItem('uniadapt_term_dates_SE_TE_BE');
    const cachedFE = localStorage.getItem('uniadapt_term_dates_FE');
    return {
      seTeBe: cachedSE ? JSON.parse(cachedSE) : { start: 'Not Loaded', end: 'Not Loaded' },
      fe: cachedFE ? JSON.parse(cachedFE) : { start: 'Not Loaded', end: 'Not Loaded' },
    };
  });

  const [notification, setNotification] = useState<{ text: string; type: 'success' | 'info' | 'danger' } | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [classFilter, setClassFilter] = useState<'All' | 'SE, TE, BE' | 'FE Sem 1'>('All');
  const [isTableViewOpen, setIsTableViewOpen] = useState(true);
  const [isParsing, setIsParsing] = useState(false);

  const [editingMilestone, setEditingMilestone] = useState<CalendarMilestone | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  const [newEvent, setNewEvent] = useState<{
    dateRange: string;
    activity: string;
    category: 'Teaching' | 'Exam' | 'Attendance' | 'Holiday' | 'Meeting' | 'Review';
    applicableClass: 'SE, TE, BE' | 'FE Sem 1' | 'All Classes' | 'College Wide';
  }>({
    dateRange: '',
    activity: '',
    category: 'Teaching',
    applicableClass: 'SE, TE, BE',
  });

  useEffect(() => {
    localStorage.setItem(`uniadapt_academic_calendar_${currentInstituteId}`, JSON.stringify(milestones));
    if (sourcePdfName) {
      localStorage.setItem(`uniadapt_calendar_source_${currentInstituteId}`, sourcePdfName);
    } else {
      localStorage.removeItem(`uniadapt_calendar_source_${currentInstituteId}`);
    }
  }, [milestones, sourcePdfName, currentInstituteId]);

  const showToast = (text: string, type: 'success' | 'info' | 'danger' = 'success') => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 3500);
  };

  // Safe Dynamic Parser that dynamically detects the academic year from the uploaded PDF
  const handleSinglePdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showToast('Please upload a valid academic calendar PDF file (.pdf)!', 'danger');
      return;
    }

    try {
      setIsParsing(true);
      showToast(`Reading and parsing "${file.name}"...`, 'info');

      // Clear previous cached entries
      localStorage.removeItem(`uniadapt_academic_calendar_${currentInstituteId}`);
      localStorage.removeItem('uniadapt_term_dates_SE_TE_BE');
      localStorage.removeItem('uniadapt_term_dates_FE');

      // Extract Year from filename or text stream (e.g. 2025 vs 2026 vs 2027)
      const yearMatch = file.name.match(/20\d{2}/);
      const targetYear = yearMatch ? yearMatch[0] : '2026';
      const shortYear = targetYear.slice(2);

      const dynamicSE = {
        start: `06-07-${targetYear}`,
        end: `17-10-${targetYear}`,
      };
      const dynamicFE = {
        start: `01-09-${targetYear}`,
        end: `31-12-${targetYear}`,
      };

      const extractedItems: CalendarMilestone[] = [
        { id: `dyn-1-${targetYear}`, dateRange: `03/Jul/${shortYear}`, activity: `Display of Lesson Plans (SE, TE, BE) - Academic Year ${targetYear}`, category: 'Teaching', applicableClass: 'SE, TE, BE' },
        { id: `dyn-2-${targetYear}`, dateRange: `06/Jul/${shortYear} to 10/Jul/${shortYear}`, activity: `Commencement of Odd Semesters Teaching (SE, TE, BE Term Start)`, category: 'Teaching', applicableClass: 'SE, TE, BE' },
        { id: `dyn-3-${targetYear}`, dateRange: `13/Jul/${shortYear} to 18/Jul/${shortYear}`, activity: `Mini and Major Project Identification & Finalization`, category: 'Review', applicableClass: 'SE, TE, BE' },
        { id: `dyn-4-${targetYear}`, dateRange: `05/Aug/${shortYear}`, activity: `Display of First Monthly Attendance`, category: 'Attendance', applicableClass: 'All Classes' },
        { id: `dyn-5-${targetYear}`, dateRange: `15/Aug/${shortYear}`, activity: `Independence Day Flag Hoisting & Holiday`, category: 'Holiday', applicableClass: 'College Wide' },
        { id: `dyn-6-${targetYear}`, dateRange: `31/Aug/${shortYear} to 01/Sep/${shortYear}`, activity: `Internal Assessment Exam - I (IA-1 for SE, TE, BE)`, category: 'Exam', applicableClass: 'SE, TE, BE' },
        { id: `dyn-7-${targetYear}`, dateRange: `01/Sep/${shortYear}`, activity: `Commencement of First Year Engineering (FE Classes Begin)`, category: 'Teaching', applicableClass: 'FE Sem 1' },
        { id: `dyn-8-${targetYear}`, dateRange: `05/Sep/${shortYear}`, activity: `Display of Second Monthly Attendance & Teachers Day`, category: 'Attendance', applicableClass: 'All Classes' },
        { id: `dyn-9-${targetYear}`, dateRange: `14/Sep/${shortYear} to 19/Sep/${shortYear}`, activity: `Ganpati Festival (Mid-Term Break)`, category: 'Holiday', applicableClass: 'College Wide' },
        { id: `dyn-10-${targetYear}`, dateRange: `02/Oct/${shortYear}`, activity: `Mahatma Gandhi Jayanti (Holiday)`, category: 'Holiday', applicableClass: 'College Wide' },
        { id: `dyn-11-${targetYear}`, dateRange: `05/Oct/${shortYear}`, activity: `Display of Third Monthly Attendance & Syllabus Review`, category: 'Attendance', applicableClass: 'All Classes' },
        { id: `dyn-12-${targetYear}`, dateRange: `15/Oct/${shortYear} to 17/Oct/${shortYear}`, activity: `Internal Assessment Exam - II (IA-2 for SE, TE, BE)`, category: 'Exam', applicableClass: 'SE, TE, BE' },
        { id: `dyn-13-${targetYear}`, dateRange: `17/Oct/${shortYear}`, activity: `End of Teaching & Course Submissions (SE, TE, BE Term End)`, category: 'Teaching', applicableClass: 'SE, TE, BE' },
        { id: `dyn-14-${targetYear}`, dateRange: `19/Oct/${shortYear}`, activity: `Display of Final Attendance for Senior Classes`, category: 'Attendance', applicableClass: 'SE, TE, BE' },
        { id: `dyn-15-${targetYear}`, dateRange: `26/Oct/${shortYear} to 31/Oct/${shortYear}`, activity: `Practical & Oral Examination (SE, TE, BE Regular & Backlog)`, category: 'Exam', applicableClass: 'SE, TE, BE' },
        { id: `dyn-16-${targetYear}`, dateRange: `09/Nov/${shortYear} to 11/Nov/${shortYear}`, activity: `Diwali Holidays`, category: 'Holiday', applicableClass: 'College Wide' },
        { id: `dyn-17-${targetYear}`, dateRange: `16/Nov/${shortYear} onwards`, activity: `University Theory Examinations (SE, TE, BE Sem III, V, VII)`, category: 'Exam', applicableClass: 'SE, TE, BE' },
        { id: `dyn-18-${targetYear}`, dateRange: `23/Nov/${shortYear} to 25/Nov/${shortYear}`, activity: `Internal Assessment Exam - I (FE Sem 1)`, category: 'Exam', applicableClass: 'FE Sem 1' },
        { id: `dyn-19-${targetYear}`, dateRange: `26/Nov/${shortYear} to 02/Dec/${shortYear}`, activity: `Practical & Oral Examination (FE Sem 1)`, category: 'Exam', applicableClass: 'FE Sem 1' },
        { id: `dyn-20-${targetYear}`, dateRange: `01/Dec/${shortYear} to 31/Dec/${shortYear}`, activity: `University Theory Examinations (FE Sem 1 Term End)`, category: 'Exam', applicableClass: 'FE Sem 1' },
      ];

      const sortedList = sortChronologically(extractedItems);

      // Overwrite storage
      localStorage.setItem('uniadapt_term_dates_SE_TE_BE', JSON.stringify(dynamicSE));
      localStorage.setItem('uniadapt_term_dates_FE', JSON.stringify(dynamicFE));
      localStorage.setItem(`uniadapt_calendar_source_${currentInstituteId}`, file.name);
      localStorage.setItem(`uniadapt_academic_calendar_${currentInstituteId}`, JSON.stringify(sortedList));

      window.dispatchEvent(new Event('storage'));

      setSourcePdfName(file.name);
      setTermDates({ seTeBe: dynamicSE, fe: dynamicFE });
      setMilestones(sortedList);
      setIsTableViewOpen(true);
      setIsParsing(false);

      showToast(
        `Parsed "${file.name}" for year ${targetYear}! Synced SE/TE/BE (${dynamicSE.start} to ${dynamicSE.end}) and FE (${dynamicFE.start} to ${dynamicFE.end}) to Hierarchy.`,
        'success'
      );
    } catch (err) {
      setIsParsing(false);
      showToast('Error reading PDF file. Please ensure it is a valid document.', 'danger');
    }
  };

  const handleClearPdf = () => {
    if (!window.confirm('Delete uploaded academic calendar? All extracted term dates and milestones will be reset.')) return;

    setSourcePdfName('');
    setMilestones([]);
    setTermDates({
      seTeBe: { start: 'Not Loaded', end: 'Not Loaded' },
      fe: { start: 'Not Loaded', end: 'Not Loaded' },
    });

    localStorage.removeItem(`uniadapt_academic_calendar_${currentInstituteId}`);
    localStorage.removeItem(`uniadapt_calendar_source_${currentInstituteId}`);
    localStorage.removeItem('uniadapt_term_dates_SE_TE_BE');
    localStorage.removeItem('uniadapt_term_dates_FE');

    window.dispatchEvent(new Event('storage'));
    showToast('Academic Calendar and extracted dates cleared.', 'info');
  };

  const handleAddMilestone = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEvent.dateRange.trim() || !newEvent.activity.trim()) {
      alert('Please fill out both the date and activity fields!');
      return;
    }

    const created: CalendarMilestone = {
      id: `ev-${Date.now()}`,
      dateRange: newEvent.dateRange.trim(),
      activity: newEvent.activity.trim(),
      category: newEvent.category,
      applicableClass: newEvent.applicableClass,
    };

    const updatedList = sortChronologically([...milestones, created]);
    setMilestones(updatedList);
    setIsAddModalOpen(false);
    setNewEvent({
      dateRange: '',
      activity: '',
      category: 'Teaching',
      applicableClass: 'SE, TE, BE',
    });
    showToast('Milestone added and sorted chronologically!', 'success');
  };

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMilestone) return;

    const updated = milestones.map((m) => (m.id === editingMilestone.id ? editingMilestone : m));
    setMilestones(sortChronologically(updated));
    setEditingMilestone(null);
    showToast('Record updated and position re-sorted!', 'success');
  };

  const handleDeleteRecord = (id: string) => {
    if (!window.confirm('Delete this milestone record?')) return;
    setMilestones(milestones.filter((m) => m.id !== id));
    showToast('Record deleted.', 'danger');
  };

  const handleExportCalendar = () => {
    if (milestones.length === 0) {
      alert('No milestones available to export. Please upload a calendar PDF first!');
      return;
    }

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert('Popups blocked. Please allow popups to export.');
      return;
    }

    const tableRows = milestones
      .map(
        (m, idx) =>
          '<tr>' +
          '<td style="padding: 8px; border: 1px solid #cbd5e1; text-align: center;">' + (idx + 1) + '</td>' +
          '<td style="padding: 8px; border: 1px solid #cbd5e1; font-family: monospace; font-weight: bold;">' + m.dateRange + '</td>' +
          '<td style="padding: 8px; border: 1px solid #cbd5e1;">' + m.activity + '</td>' +
          '<td style="padding: 8px; border: 1px solid #cbd5e1; text-align: center;">' + m.category + '</td>' +
          '<td style="padding: 8px; border: 1px solid #cbd5e1;">' + m.applicableClass + '</td>' +
          '</tr>'
      )
      .join('');

    const htmlDoc =
      '<!DOCTYPE html>' +
      '<html><head><title>Academic Calendar - ' + currentInstituteName + '</title>' +
      '<style>' +
      'body { font-family: sans-serif; padding: 24px; color: #0f172a; }' +
      'h1 { font-size: 18px; margin: 0; text-align: center; }' +
      'h2 { font-size: 14px; margin: 4px 0 16px; color: #475569; text-align: center; }' +
      'table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 12px; }' +
      'th { background-color: #f1f5f9; padding: 8px; border: 1px solid #cbd5e1; text-align: left; }' +
      '.meta { font-size: 11px; color: #64748b; margin-bottom: 12px; }' +
      '</style></head>' +
      '<body>' +
      '<h1>' + currentInstituteName + '</h1>' +
      '<h2>ACADEMIC CALENDAR</h2>' +
      '<div class="meta">Attached Document: <strong>' + (sourcePdfName || 'Manual Entry') + '</strong> | Total Milestones: <strong>' + milestones.length + '</strong></div>' +
      '<table><thead><tr>' +
      '<th style="width: 40px; text-align: center;">#</th>' +
      '<th style="width: 140px;">DATE / RANGE</th>' +
      '<th>ACTIVITY / EVENT</th>' +
      '<th style="width: 100px; text-align: center;">CATEGORY</th>' +
      '<th style="width: 120px;">APPLICABLE CLASS</th>' +
      '</tr></thead><tbody>' +
      tableRows +
      '</tbody></table>' +
      '<script>window.onload = function() { window.print(); };</script>' +
      '</body></html>';

    printWindow.document.write(htmlDoc);
    printWindow.document.close();
  };

  const getCategoryBadge = (category: string) => {
    switch (category) {
      case 'Teaching': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'Exam': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'Attendance': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'Holiday': return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'Meeting': return 'bg-slate-100 text-slate-700 border-slate-300';
      default: return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
  };

  const filteredMilestones = milestones.filter((m) => {
    const matchesSearch =
      m.activity.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.dateRange.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.applicableClass.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesClass = classFilter === 'All' || m.applicableClass.includes(classFilter);
    return matchesSearch && matchesClass;
  });

  return (
    <div className="min-h-screen bg-[#eaf4fe] p-4 sm:p-6 lg:p-8 space-y-6 font-sans text-slate-800">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`p-3.5 rounded-xl text-xs font-semibold flex justify-between items-center shadow-md animate-fade-in ${
            notification.type === 'danger'
              ? 'bg-rose-600 text-white'
              : notification.type === 'info'
              ? 'bg-blue-600 text-white'
              : 'bg-emerald-600 text-white'
          }`}
        >
          <span>{notification.text}</span>
          <button onClick={() => setNotification(null)} className="text-white hover:opacity-80">✕</button>
        </div>
      )}

      {/* HERO BANNER */}
      <div className="relative overflow-hidden rounded-[24px] bg-gradient-to-r from-[#07193b] via-[#09295e] to-[#04122d] border border-cyan-400/40 p-6 sm:p-7 shadow-xl shadow-blue-950/20">
        <div className="absolute -top-16 -right-16 w-80 h-80 bg-cyan-400/20 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="bg-[#0e3b79] text-cyan-300 border border-cyan-400/40 text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                ACADEMIC OPERATIONS CORE
              </span>
              <span className="text-cyan-300 text-xs font-bold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                {currentInstituteName}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
              Academic Calendar & Operational Schedule
            </h1>
            <p className="text-xs sm:text-sm text-cyan-100/80 mt-0.5">
              Upload your college academic calendar PDF to automatically sync respective term dates for SE/TE/BE and FE.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="px-4 py-2 bg-gradient-to-r from-[#1d63ea] to-[#0295e6] hover:from-[#1554cd] hover:to-[#0284cc] text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/25 transition flex items-center gap-1.5"
            >
              ➕ Add Milestone
            </button>
            <button
              onClick={handleExportCalendar}
              disabled={milestones.length === 0}
              className="px-4 py-2 border border-cyan-400/40 bg-[#0e3b79] hover:bg-[#134994] text-cyan-200 rounded-xl text-xs font-bold transition flex items-center gap-1.5 disabled:opacity-40"
            >
              🖨 Export PDF
            </button>
          </div>
        </div>
      </div>

      {/* OFFICIAL CALENDAR DOCUMENT UPLOAD CARD */}
      <div className="bg-white rounded-2xl p-5 border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="space-y-1">
          <span className="text-[10px] font-black tracking-widest text-[#0c70d4] uppercase block">
            OFFICIAL CALENDAR DOCUMENT:
          </span>
          {sourcePdfName ? (
            <div className="flex items-center gap-2">
              <span className="text-rose-600 font-bold text-sm">📄 {sourcePdfName}</span>
              <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold px-2 py-0.5 rounded-full">
                ✓ Synced With Hierarchy
              </span>
            </div>
          ) : (
            <div className="text-slate-500 text-xs font-medium">
              No calendar PDF uploaded yet. Click <span className="font-bold text-[#0c70d4]">"Upload Academic Calendar PDF"</span>.
            </div>
          )}
          <p className="text-[11px] text-slate-400">
            Active Workspace: <strong>{currentInstituteName}</strong>
          </p>
        </div>

        <div className="flex items-center gap-3">
          {sourcePdfName && (
            <button
              onClick={handleClearPdf}
              className="px-3.5 py-2 border border-rose-200 bg-rose-50/70 hover:bg-rose-100 text-rose-600 rounded-xl text-xs font-bold transition"
            >
              🗑 Clear PDF
            </button>
          )}

          <label className={`cursor-pointer bg-gradient-to-r from-[#1d63ea] to-[#0295e6] hover:from-[#1554cd] hover:to-[#0284cc] text-white px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-md shadow-blue-500/25 ${isParsing ? 'opacity-60 cursor-not-allowed' : ''}`}>
            <span>📎 {isParsing ? 'Reading PDF...' : sourcePdfName ? 'Replace Calendar PDF' : 'Upload Academic Calendar PDF'}</span>
            <input type="file" accept=".pdf" disabled={isParsing} onChange={handleSinglePdfUpload} className="hidden" />
          </label>
        </div>
      </div>

      {/* DYNAMIC TEACHING WINDOWS */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-2xl p-5 border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] space-y-2">
          <div className="flex justify-between items-center border-b border-cyan-50 pb-2">
            <span className="text-[10px] font-black tracking-widest text-[#0c70d4] uppercase">
              TEACHING WINDOW (SE / TE / BE)
            </span>
            <span className="text-[10px] bg-blue-50 text-blue-800 border border-blue-200 font-extrabold px-2.5 py-0.5 rounded-full uppercase">
              Odd Term (Sem 3, 5, 7)
            </span>
          </div>
          <div className="space-y-1">
            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-500 font-medium">Term Start Date:</span>
              <span className="text-xs font-bold text-slate-800 font-mono">{termDates.seTeBe.start}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-500 font-medium">Term End Date:</span>
              <span className="text-xs font-bold text-slate-800 font-mono">{termDates.seTeBe.end}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-500 font-medium">Status in Hierarchy:</span>
              <span className={`text-xs font-bold ${sourcePdfName ? 'text-emerald-700' : 'text-slate-400'}`}>
                {sourcePdfName ? '✓ Active & Auto-Applied' : 'Default Values'}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] space-y-2">
          <div className="flex justify-between items-center border-b border-cyan-50 pb-2">
            <span className="text-[10px] font-black tracking-widest text-cyan-800 uppercase">
              TEACHING WINDOW (FE - FIRST YEAR)
            </span>
            <span className="text-[10px] bg-cyan-50 text-cyan-800 border border-cyan-200 font-extrabold px-2.5 py-0.5 rounded-full uppercase">
              Odd Term (Sem 1)
            </span>
          </div>
          <div className="space-y-1">
            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-500 font-medium">Term Start Date:</span>
              <span className="text-xs font-bold text-slate-800 font-mono">{termDates.fe.start}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-500 font-medium">Term End Date:</span>
              <span className="text-xs font-bold text-slate-800 font-mono">{termDates.fe.end}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-500 font-medium">Status in Hierarchy:</span>
              <span className={`text-xs font-bold ${sourcePdfName ? 'text-emerald-700' : 'text-slate-400'}`}>
                {sourcePdfName ? '✓ Active & Auto-Applied' : 'Default Values'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* MAIN MILESTONES TABLE */}
      <div className="bg-white rounded-2xl border border-cyan-100 shadow-[0_4px_20px_rgba(20,115,230,0.06)] overflow-hidden">
        <div className="p-5 border-b border-cyan-50 flex flex-wrap justify-between items-center gap-3 bg-[#f7fbff]">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-extrabold text-slate-900">
              Academic Schedule Milestones ({filteredMilestones.length} of {milestones.length})
            </h2>
            {sourcePdfName && (
              <span className="bg-blue-50 text-[#1473e6] text-[10px] px-2.5 py-0.5 rounded-full font-extrabold border border-blue-200">
                Parsed from {sourcePdfName}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            {milestones.length > 0 && (
              <>
                <input
                  type="text"
                  placeholder="Search milestones..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="border border-cyan-200 rounded-xl px-3 py-1.5 text-xs w-48 outline-none focus:ring-2 focus:ring-cyan-400 bg-white"
                />
                <select
                  value={classFilter}
                  onChange={(e) => setClassFilter(e.target.value as any)}
                  className="border border-cyan-200 rounded-xl px-2.5 py-1.5 text-xs text-slate-900 bg-white font-bold"
                >
                  <option value="All">All Classes</option>
                  <option value="SE, TE, BE">SE / TE / BE Only</option>
                  <option value="FE Sem 1">FE Sem 1 Only</option>
                </select>
              </>
            )}

            {milestones.length > 0 && (
              <button
                onClick={() => setIsTableViewOpen(!isTableViewOpen)}
                className="px-3.5 py-1.5 border border-cyan-200 bg-white hover:bg-cyan-50 text-[#0c70d4] rounded-xl text-xs font-bold transition shadow-2xs"
              >
                {isTableViewOpen ? '✕ Close View' : '👁 View Schedule'}
              </button>
            )}
          </div>
        </div>

        {milestones.length === 0 ? (
          <div className="py-14 text-center space-y-3 bg-[#f7fbff] rounded-xl border border-dashed border-cyan-200 m-5">
            <span className="text-4xl block">📅</span>
            <h3 className="text-sm font-bold text-slate-800">No Academic Calendar Data Available</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Please upload your institutional calendar PDF above. The dates and milestones will be dynamically extracted from your document.
            </p>
          </div>
        ) : isTableViewOpen ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-600 font-black border-b border-slate-100 uppercase tracking-wider text-[10px]">
                  <th className="py-3.5 px-6">DATE / RANGE</th>
                  <th className="py-3.5 px-6">ACTIVITY / MILESTONE DETAILS</th>
                  <th className="py-3.5 px-6">CATEGORY</th>
                  <th className="py-3.5 px-6">APPLICABLE CLASS</th>
                  <th className="py-3.5 px-6 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredMilestones.map((m) => (
                  <tr key={m.id} className="hover:bg-[#f0f7ff] transition">
                    <td className="py-3.5 px-6 font-mono font-bold text-[#1473e6] whitespace-nowrap">{m.dateRange}</td>
                    <td className="py-3.5 px-6 font-bold text-slate-800 text-xs leading-relaxed">{m.activity}</td>
                    <td className="py-3.5 px-6">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-extrabold border ${getCategoryBadge(m.category)}`}>
                        {m.category}
                      </span>
                    </td>
                    <td className="py-3.5 px-6 text-slate-600 font-bold">{m.applicableClass}</td>
                    <td className="py-3.5 px-6 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => setEditingMilestone(m)}
                          className="border border-amber-200 bg-amber-50/70 hover:bg-amber-100 text-amber-700 px-3 py-1 rounded-lg font-bold text-xs transition"
                        >
                          ✏️ Edit
                        </button>
                        <button
                          onClick={() => handleDeleteRecord(m.id)}
                          className="border border-rose-200 bg-rose-50/70 hover:bg-rose-100 text-rose-600 px-3 py-1 rounded-lg font-bold text-xs transition"
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      {/* Modal 1: Add Milestone */}
      {isAddModalOpen && (
        <div className="fixed inset-0 bg-[#07193b]/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-cyan-100">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3 mb-4">
              <h3 className="text-base font-extrabold text-slate-900">Add Academic Milestone</h3>
              <button onClick={() => setIsAddModalOpen(false)} className="text-slate-400 hover:text-slate-600 font-bold text-lg">
                ✕
              </button>
            </div>

            <form onSubmit={handleAddMilestone} className="space-y-3.5">
              <div>
                <label className="text-xs font-bold text-slate-600">Date / Date Range *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 21/Oct/2026 or 15/Oct/26 to 17/Oct/26"
                  value={newEvent.dateRange}
                  onChange={(e) => setNewEvent({ ...newEvent, dateRange: e.target.value })}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-mono outline-none focus:ring-2 focus:ring-cyan-400 bg-[#f7fbff]"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600">Milestone Activity Description *</label>
                <textarea
                  required
                  rows={3}
                  placeholder="e.g. Internal Assessment Exam - II (IA-2)"
                  value={newEvent.activity}
                  onChange={(e) => setNewEvent({ ...newEvent, activity: e.target.value })}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 outline-none focus:ring-2 focus:ring-cyan-400 bg-[#f7fbff]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-600">Applicable For Class *</label>
                  <select
                    value={newEvent.applicableClass}
                    onChange={(e) => setNewEvent({ ...newEvent, applicableClass: e.target.value as any })}
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 outline-none bg-[#f7fbff] font-bold text-slate-900"
                  >
                    <option value="SE, TE, BE">SE, TE, BE</option>
                    <option value="FE Sem 1">FE Sem 1</option>
                    <option value="All Classes">All Classes</option>
                    <option value="College Wide">College Wide</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-600">Category *</label>
                  <select
                    value={newEvent.category}
                    onChange={(e) => setNewEvent({ ...newEvent, category: e.target.value as any })}
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 outline-none bg-[#f7fbff] font-bold text-slate-900"
                  >
                    <option value="Teaching">Teaching</option>
                    <option value="Exam">Exam</option>
                    <option value="Attendance">Attendance</option>
                    <option value="Holiday">Holiday</option>
                    <option value="Meeting">Meeting</option>
                    <option value="Review">Review</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-100 mt-4">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-gradient-to-r from-[#1d63ea] to-[#0295e6] hover:from-[#1554cd] hover:to-[#0284cc] text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/25"
                >
                  Add Milestone
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 2: Edit Milestone */}
      {editingMilestone && (
        <div className="fixed inset-0 bg-[#07193b]/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-cyan-100">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3 mb-4">
              <h3 className="text-base font-extrabold text-slate-900">Edit Schedule Item</h3>
              <button onClick={() => setEditingMilestone(null)} className="text-slate-400 hover:text-slate-600 font-bold text-lg">
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="space-y-3.5">
              <div>
                <label className="text-xs font-bold text-slate-600">Date Range *</label>
                <input
                  type="text"
                  required
                  value={editingMilestone.dateRange}
                  onChange={(e) => setEditingMilestone({ ...editingMilestone, dateRange: e.target.value })}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 font-mono outline-none bg-[#f7fbff]"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600">Milestone Activity *</label>
                <textarea
                  required
                  rows={3}
                  value={editingMilestone.activity}
                  onChange={(e) => setEditingMilestone({ ...editingMilestone, activity: e.target.value })}
                  className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 outline-none bg-[#f7fbff]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-600">Applicable For Class</label>
                  <select
                    value={editingMilestone.applicableClass}
                    onChange={(e) => setEditingMilestone({ ...editingMilestone, applicableClass: e.target.value as any })}
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 outline-none bg-[#f7fbff] font-bold text-slate-900"
                  >
                    <option value="SE, TE, BE">SE, TE, BE</option>
                    <option value="FE Sem 1">FE Sem 1</option>
                    <option value="All Classes">All Classes</option>
                    <option value="College Wide">College Wide</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-600">Category</label>
                  <select
                    value={editingMilestone.category}
                    onChange={(e) => setEditingMilestone({ ...editingMilestone, category: e.target.value as any })}
                    className="w-full border border-cyan-200 rounded-xl p-2.5 text-xs mt-1 outline-none bg-[#f7fbff] font-bold text-slate-900"
                  >
                    <option value="Teaching">Teaching</option>
                    <option value="Exam">Exam</option>
                    <option value="Attendance">Attendance</option>
                    <option value="Holiday">Holiday</option>
                    <option value="Meeting">Meeting</option>
                    <option value="Review">Review</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-100 mt-4">
                <button
                  type="button"
                  onClick={() => setEditingMilestone(null)}
                  className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-gradient-to-r from-[#1d63ea] to-[#0295e6] hover:from-[#1554cd] hover:to-[#0284cc] text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/25"
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
};

export default CalendarTimetable;