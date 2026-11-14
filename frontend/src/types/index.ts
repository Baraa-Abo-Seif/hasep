export interface APIResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
  errors?: string[];
}

export interface DocumentPageInfo {
  id: string;
  page_number: number;
  image_url: string;
  preview_url?: string;
  width?: number;
  height?: number;
}

export interface DocumentItem {
  id: string;
  title: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  document_type: string;
  status: string;
  error_message?: string;
  pages: DocumentPageInfo[];
  created_at: string;
  updated_at: string;
}

export interface ProcessingStatus {
  document_id: string;
  status: string;
  progress_percentage: number;
  stage: string;
  error_message?: string;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
  polygon?: number[];
}

export interface ExtractedCell {
  value: string | number | boolean | null;
  original_text?: string;
  data_type: string;
  confidence?: number;
  needs_review: boolean;
  uncertainty_reason?: string;
  bounding_box?: BoundingBox;
}

export interface ExtractedRow {
  row_number: number;
  row_id?: string;
  values: Record<string, ExtractedCell>;
}

export interface ExtractedColumn {
  key: string;
  label: string;
  data_type: string;
  order_index: number;
  is_required: boolean;
}

export interface ExtractedTable {
  table_id: string;
  title: string;
  description?: string;
  confidence_score?: number;
  page_number: number;
  columns: ExtractedColumn[];
  rows: ExtractedRow[];
}

export interface ValidationError {
  table_id?: string;
  row_number?: number;
  column_key?: string;
  validation_type: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
}

export interface DocumentReviewData {
  document_id: string;
  document_title: string;
  document_type: string;
  status: string;
  is_approved: boolean;
  tables: ExtractedTable[];
  validation_errors: ValidationError[];
  image_pages: DocumentPageInfo[];
}

export interface MicrosoftStatus {
  is_connected: boolean;
  email?: string;
  display_name?: string;
  account_type?: 'personal' | 'work_school';
  expires_at?: string;
}

export interface ExcelWorkbook {
  id: string;
  name: string;
  web_url?: string;
  last_modified_date_time?: string;
}

export interface ExcelWorksheet {
  id: string;
  name: string;
  position?: number;
  visibility?: string;
}

export interface ExcelTable {
  id: string;
  name: string;
  show_headers: boolean;
  columns: string[];
}

export interface ColumnMappingItem {
  extracted_key: string;
  extracted_label: string;
  excel_column_name: string;
  data_type: string;
}

export interface ExportPreview {
  document_id: string;
  table_id: string;
  workbook_name: string;
  target_table_name?: string;
  mapped_columns: ColumnMappingItem[];
  unmapped_columns: string[];
  missing_required_columns: string[];
  total_rows_to_export: number;
  sample_preview_rows: Record<string, any>[];
  account_type: string;
  export_mode: string;
}

export interface ExportResult {
  export_id: string;
  status: string;
  rows_exported: number;
  export_mode: string;
  target_workbook: string;
  target_worksheet?: string;
  target_table?: string;
  verified: boolean;
  verification_details: Record<string, any>;
  message: string;
}

export interface DashboardStats {
  total_documents: number;
  pending_reviews: number;
  successful_exports: number;
  failed_operations: number;
}

export interface EmployeeAttendanceItem {
  employee_name: string;
  status: 'حاضر' | 'غائب' | 'إجازة' | 'مغادرة' | '';
  entry_time?: string;
  exit_time?: string;
  duration_hours: string | number;
  notes?: string;
}

export interface PurchaseItem {
  item: string;
  amount: string | number;
  invoice_number?: string;
  notes?: string;
}

export interface ExpenseItem {
  item: string;
  amount: string | number;
  notes?: string;
}

export interface SalesData {
  sales: string | number;
  returns: string | number;
  net_sale: string | number;
  orders: string | number;
  kareem: string | number;
  ashaayi: string | number;
  visa: string | number;
  total_applications: string | number;
  total_sale: string | number;
}

export interface SummaryData {
  total_expenses: string | number;
  total_purchases: string | number;
  total_expenses_and_purchases: string | number;
  previous_balance: string | number;
  increase: string | number;
  decrease: string | number;
  current_balance: string | number;
  handwritten_current_balance?: string | number | null;
}

export interface CalculationMismatch {
  equation_id: string;
  field_name: string;
  arabic_label: string;
  extracted_value?: string | number | null;
  calculated_value: string | number;
  difference: string | number;
  severity: 'error' | 'warning';
  message: string;
}

export interface OCRUncertainty {
  field_path: string;
  arabic_label: string;
  raw_extracted_text?: string;
  normalized_value: any;
  confidence: number;
  reason: string;
  resolved: boolean;
}

export interface FinancialFormData {
  form_date: string;
  day_of_week: string;
  attendance: EmployeeAttendanceItem[];
  purchases: PurchaseItem[];
  expenses: ExpenseItem[];
  sales: SalesData;
  summary: SummaryData;
  calculation_mismatches: CalculationMismatch[];
  ocr_uncertainties: OCRUncertainty[];
  is_mathematically_valid: boolean;
  all_uncertainties_resolved: boolean;
}

export interface FinancialRecordItem {
  id: string;
  document_id: string;
  form_date: string;
  day_of_week: string;
  total_sales: string;
  total_expenses: string;
  total_purchases: string;
  current_balance: string;
  is_approved: boolean;
  approved_at?: string;
  excel_sync_status: string;
  pdf_url?: string;
}

export interface FinancialKPISummary {
  count: number;
  total_sales_sum: string;
  total_expenses_sum: string;
  total_purchases_sum: string;
  currency: string;
}
