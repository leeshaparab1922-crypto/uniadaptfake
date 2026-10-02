export interface Institute {
  id: string;
  name: string;
  timezone: string;
}

export interface Department {
  id: string;
  institute_id: string;
  code: string;
  name: string;
}

export interface Program {
  id: string;
  department_id: string;
  code: string;
  name: string;
  duration_semesters: number;
}

export interface Batch {
  id: string;
  program_id: string;
  start_year: number;
  end_year: number;
}

export interface Semester {
  id: string;
  batch_id: string;
  number: number;
  start_date: string;
  end_date: string;
}

export interface Section {
  id: string;
  semester_id: string;
  name: string;
  capacity: number;
}
