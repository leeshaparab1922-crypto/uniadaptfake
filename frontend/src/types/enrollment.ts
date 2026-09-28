export interface EnrollmentOut {
  id: string;
  subject_instance_id: string;
  elective_group_id: string | null;
  status: "ACTIVE" | "CLOSED";
  auto_allocated: boolean;
  effective_from: string;
  effective_to: string | null;
}

export interface PromotionPreviewItem {
  student_id: string;
  roll_number: string;
  from_section_id: string;
  to_section_id: string;
  capacity_conflict: boolean;
}

export interface PromotionPreviewResponse {
  items: PromotionPreviewItem[];
  has_conflicts: boolean;
}
