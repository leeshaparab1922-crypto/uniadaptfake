export interface StudentListItem {
  id: string;
  user_id: string;
  roll_number: string;
  department_id: string;
  batch_id: string;
  section_id: string;
  current_semester_no: number;
  email: string;
  full_name: string;
}

export interface StudentListResponse {
  items: StudentListItem[];
  total: number;
  limit: number;
  offset: number;
}
