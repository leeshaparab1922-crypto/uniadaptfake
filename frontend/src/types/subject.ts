export type SubjectType = "CORE" | "ELECTIVE" | "LAB";

export interface ElectiveGroup {
  id: string;
  program_id: string;
  semester_no: number;
  name: string;
  required: boolean;
}

export interface Subject {
  id: string;
  program_id: string;
  semester_no: number;
  code: string;
  name: string;
  credits: number;
  type: SubjectType;
  elective_group_id: string | null;
}

export interface Unit {
  id: string;
  order_index: number;
  name: string;
  weightage: number;
}

export type TeacherAssignmentRole = "PRIMARY" | "CO";

export interface SubjectInstance {
  id: string;
  subject_id: string;
  section_id: string;
  exam_at: string | null;
  status: "DRAFT" | "ACTIVE";
}
