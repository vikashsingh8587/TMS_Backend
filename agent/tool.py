from langchain_core.tools import tool

from services.database_service import (
    get_all_students,
  
    get_pending_fees_students,
    get_pending_fees_students_by_name,
    get_total_fees_pending_siblings,
    get_last_kth_payment,
    process_fees_payment,
    get_total_collected_in_month,
    get_unpaid_students_this_month,
    get_student_overall_fee_history,
    create_new_student,
    deactivate_student,
    hard_delete_student,
    filter_students_by_name,
    filter_students_by_class,
    create_new_multiple_students,
)


# ============================================================
# READ-ONLY TOOLS
# ============================================================

@tool
def get_all_students_tool():
    """
    Get all students from the tuition management database.

    Use this when the user asks:
    - show all students
    - list students
    - how many students are there
    - give me student records
    """
    return get_all_students()


@tool
def get_pending_fees_tool():
    """
    Get all students who currently have pending tuition fees.

    Use this when the user asks:
    - who has pending fees
    - who has unpaid fees
    - show students with dues
    - which students have outstanding fees
    """
    return get_pending_fees_students()


@tool
def get_pending_fees_by_student_name_tool(name: str):
    """
    Find pending fee information for a student by name.

    Args:
        name: Full or partial student name.

    Use this when the user asks:
    - Does Rahul have pending fees?
    - Show pending fees for Amit
    - How much does Priya owe?
    """
    return get_pending_fees_students_by_name(name)


@tool
def get_student_sibling_pending_fees_tool(student_id: int):
    """
    Get the total pending fees for the student's family/siblings.

    Args:
        student_id: ID of the student.

    Use this when the user asks:
    - how much does the family owe
    - total pending fees for siblings
    - total family dues for a student
    """
    return get_total_fees_pending_siblings(student_id)


@tool
def get_student_payment_tool(student_id: int, k: int = 1):
    """
    Get the kth most recent payment of a student.

    Args:
        student_id: Student ID.
        k: Payment position. 1 means latest payment,
           2 means second latest payment, etc.

    Use this when the user asks:
    - latest payment
    - last payment
    - previous payment
    - second last payment
    """
    return get_last_kth_payment(student_id, k)


@tool
def get_student_fee_history_tool(student_id: int):
    """
    Get the complete fee history of a student.

    Args:
        student_id: Student ID.

    Includes available information such as:
    - student details
    - parent details
    - current due
    - payment history
    - total paid
    - transaction information

    Use this when the user asks for a student's complete fee history.
    """
    return get_student_overall_fee_history(student_id)


@tool
def get_monthly_collection_tool(month_name: str, year: int):
    """
    Get total fees collected and payment count for a particular month and year.

    Args:
        month_name: Full month name such as January, February, March.
        year: Four-digit year.

    Example:
        get_monthly_collection_tool("September", 2026)

    Use this for questions such as:
    - How much fee was collected in September?
    - How many payments were received in August 2026?
    """
    return get_total_collected_in_month(month_name, year)


@tool
def get_unpaid_students_this_month_tool():
    """
    Get students who have not properly paid their fees for the current month.

    Use this when the user asks:
    - who has not paid this month
    - unpaid students this month
    - students who haven't paid this month
    """
    return get_unpaid_students_this_month()

@tool
def search_students_by_name(search_name: str):
    """
    Search students by their name.

    Use this tool when the user wants to find students
    by full name or partial name.

    Example:
    - Find Rahul
    - Search students named Amit
    - Show students whose name contains Priya
    """

    if not search_name or not search_name.strip():
        return {
            "status": "error",
            "message": "Student name is required."
        }

    try:
        students = filter_students_by_name(
            search_name.strip()
        )

        if not students:
            return {
                "status": "success",
                "message": (
                    f"No students found matching "
                    f"'{search_name}'."
                ),
                "students": []
            }

        return {
            "status": "success",
            "count": len(students),
            "students": students
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# 2. SEARCH STUDENTS BY CLASS
# ============================================================

@tool
def search_students_by_class(class_name: str):
    """
    Find all students belonging to a specific class or grade.

    Use this tool when the user asks:
    - Show students in class 10
    - List class 8 students
    - Who is studying in class 5?
    """

    if not class_name or not class_name.strip():
        return {
            "status": "error",
            "message": "Class name is required."
        }

    try:
        students = filter_students_by_class(
            class_name.strip()
        )

        if not students:
            return {
                "status": "success",
                "message": (
                    f"No students found in "
                    f"class '{class_name}'."
                ),
                "students": []
            }

        return {
            "status": "success",
            "count": len(students),
            "class_name": class_name.strip(),
            "students": students
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }

# ============================================================
# WRITE TOOLS
# ============================================================

@tool
def process_student_fee_payment_tool(
    student_id: int,
    paid_amount: float,
    payment_mode: str = "Cash"
):
    """
    Process a student's fee payment.

    Args:
        student_id: Student ID.
        paid_amount: Amount being paid.
        payment_mode: Payment method such as Cash, UPI, Card, Bank Transfer.

    IMPORTANT:
    This changes the database and creates payment records.

    The agent must NEVER execute this tool without explicit confirmation
    from the user immediately before performing the payment.
    """
    return process_fees_payment(
        student_id,
        paid_amount,
        payment_mode
    )


@tool
def create_new_student_tool(
    full_name: str,
    monthly_fee_amount: float,
    gender: str = "Male",
    class_grade: str = None,
    school_name: str = None,
    joining_date: str = None,
    parent_id: int = None,
    father_name: str = None,
    primary_phone: str = None,
    address: str = None
):
    """
    Create a new student in the tuition database.

    Args:
        full_name: Full name of the student.
        monthly_fee_amount: Monthly tuition fee.
        gender: Student gender.
        class_grade: Student class or grade.
        school_name: Student school name.
        joining_date: Student joining date.
        parent_id: Existing parent ID if available.
        father_name: Father's name.
        primary_phone: Parent's primary phone number.
        address: Parent's address.

    IMPORTANT:
    This changes the database.
    The agent must get explicit confirmation before executing.
    """

    return create_new_student(
        full_name=full_name,
        monthly_fee_amount=monthly_fee_amount,
        gender=gender,
        class_grade=class_grade,
        school_name=school_name,
        joining_date=joining_date,
        parent_id=parent_id,
        father_name=father_name,
        primary_phone=primary_phone,
        address=address
    )


@tool
def deactivate_student_tool(student_id: int):
    """
    Deactivate a student.

    Args:
        student_id: Student ID.

    IMPORTANT:
    This changes the student's status in the database.

    The agent must ask for explicit confirmation before executing.
    """
    return deactivate_student(student_id)


@tool
def hard_delete_student_tool(student_id: int):
    """
    Permanently delete a student and linked payment/transaction records.

    Args:
        student_id: Student ID.

    WARNING:
    This is a destructive database operation and cannot be treated
    as a normal conversational action.

    NEVER execute this tool automatically.
    Require explicit confirmation immediately before execution.
    """
    return hard_delete_student(student_id)
@tool
def register_multiple_students(
    father_name: str,
    mother_name: str,
    primary_phone: str,
    address: str,
    students_list: list
):
    """
    Register a parent and multiple students under that parent.

    Use this tool when a parent wants to register
    one or more children/students.

    students_list should contain objects like:

    [
        {
            "full_name": "Rahul Sharma",
            "gender": "Male",
            "class_grade": "10",
            "school_name": "ABC School",
            "monthly_fee_amount": 2500,
            "joining_date": "2026-09-25"
        }
    ]
    """

    # -----------------------------
    # Basic validation
    # -----------------------------

    if not father_name or not father_name.strip():
        return {
            "status": "error",
            "message": "Father name is required."
        }

    if not primary_phone or not primary_phone.strip():
        return {
            "status": "error",
            "message": "Primary phone is required."
        }

    if not students_list:
        return {
            "status": "error",
            "message": "At least one student is required."
        }

    try:

        result = create_new_multiple_students(
            father_name=father_name.strip(),
            mother_name=(
                mother_name.strip()
                if mother_name
                else ""
            ),
            primary_phone=primary_phone.strip(),
            address=(
                address.strip()
                if address
                else ""
            ),
            students_list=students_list
        )

        return result

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }

# ============================================================
# TOOL GROUPS
# ============================================================

READ_ONLY_TOOLS = [
    get_all_students_tool,
    get_pending_fees_tool,
    get_pending_fees_by_student_name_tool,
    get_student_sibling_pending_fees_tool,
    get_student_payment_tool,
    get_student_fee_history_tool,
    get_monthly_collection_tool,
    get_unpaid_students_this_month_tool,
    search_students_by_name,
    search_students_by_class,
        
]


WRITE_TOOLS = [
    process_student_fee_payment_tool,
    create_new_student_tool,
    deactivate_student_tool,
    hard_delete_student_tool,
    register_multiple_students,
]


ALL_TOOLS = READ_ONLY_TOOLS + WRITE_TOOLS