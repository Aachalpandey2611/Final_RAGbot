"""
Create a sample company_policy.pdf for end-to-end testing.
"""
from fpdf import FPDF
import os

SAMPLE_TEXT = """
COMPANY POLICY DOCUMENT

1. Leave Policy

All full-time employees are entitled to 24 days of paid leave per year. Leave must be applied for at least 3 working days in advance unless it is an emergency. Unused leave can be carried forward up to a maximum of 10 days to the next calendar year. Employees on probation are entitled to 12 days of paid leave.

Sick leave of more than 3 consecutive days requires a medical certificate. Maternity leave is granted for 26 weeks as per applicable laws. Paternity leave of 5 working days is available for new fathers.

2. Work From Home Policy

Employees may work from home up to 2 days per week with prior approval from their manager. During work-from-home days, employees must be available during core hours (10 AM to 4 PM). All work-from-home arrangements must be documented in the HR portal. Internet connectivity and a suitable workspace are the responsibility of the employee.

3. Reimbursement Process

All business-related expenses must be submitted within 30 days of incurrence. Receipts or invoices are mandatory for claims above Rs. 500. Travel reimbursements require pre-approval from the department head. The finance team processes reimbursements within 15 working days of submission.

4. Code of Conduct

Employees are expected to maintain professional behavior at all times. Harassment, discrimination, or bullying of any kind will not be tolerated. Conflicts of interest must be disclosed to the HR department immediately. Use of company resources for personal purposes is strictly prohibited.

5. Data Security Policy

All company data must be handled in accordance with the data classification policy. Sharing of confidential information outside the organization requires written approval. Employees must use strong passwords and change them every 90 days. Lost or stolen devices containing company data must be reported within 24 hours.

6. Performance Review Policy

Performance reviews are conducted quarterly and annually. Employees are evaluated on key performance indicators (KPIs) set at the beginning of each quarter. Self-assessment forms must be submitted 5 days before the review meeting. Promotions and salary increments are based on performance review outcomes.

7. Training and Development

The company allocates a training budget of Rs. 50,000 per employee per year. Employees can request training programs relevant to their role through the learning management system. Mandatory compliance training must be completed within 30 days of joining. Certification reimbursements are available for pre-approved professional certifications.

8. Grievance Redressal

Employees can raise grievances through the online grievance portal or directly with the HR department. All grievances will be acknowledged within 2 working days. The grievance committee will investigate and resolve issues within 15 working days. Anonymity of the complainant will be maintained unless disclosure is necessary for resolution.

9. Exit Policy

Employees must serve a notice period of 30 days (60 days for senior roles). Exit interviews are mandatory and conducted by the HR department. All company assets must be returned before the last working day. Final settlement including pending salary, leave encashment, and bonuses will be processed within 45 days of the last working day.

10. Health and Safety

The company provides comprehensive health insurance coverage for employees and their dependents. Annual health check-ups are offered free of cost. Fire drills and safety training are conducted quarterly. First aid kits are available on every floor and employees are encouraged to familiarize themselves with emergency exits.
"""

def create_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Split into sections for multiple pages
    sections = SAMPLE_TEXT.strip().split("\n\n")
    
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, sections[0].strip(), ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "", 11)
    for section in sections[1:]:
        lines = section.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Check if it's a heading (starts with a number and period)
            if line and line[0].isdigit() and ". " in line[:4]:
                pdf.ln(3)
                pdf.set_font("Helvetica", "B", 12)
                pdf.multi_cell(0, 7, line)
                pdf.set_font("Helvetica", "", 11)
            else:
                pdf.multi_cell(0, 6, line)
            pdf.ln(2)
    
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "company_policy.pdf")
    pdf.output(output_path)
    print(f"Created: {output_path}")
    return output_path

if __name__ == "__main__":
    create_pdf()
