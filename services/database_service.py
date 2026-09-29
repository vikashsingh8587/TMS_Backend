from database import get_db_connection
from datetime import datetime
import json
import uuid
import os





# -------------------------------------------------------------
# 1. READ / FETCH FUNCTIONS
# -------------------------------------------------------------

def get_all_students():
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM student")
            return cursor.fetchall()
        finally:
            cursor.close()
    finally:
        connection.close()


def get_pending_fees_students():
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT s.Student_id, s.Full_name, lt.due_amount
                FROM Student AS s
                LEFT JOIN Last_Payment AS lt ON s.Last_Pay_id = lt.last_Payment_id
                WHERE lt.due_amount > 0 OR s.Last_Pay_id IS NULL
            """)
            students = cursor.fetchall()

            return [
                {
                    "id": student["Student_id"],
                    "name": student["Full_name"].strip(),
                    "fees_pending": float(student["due_amount"]) if student["due_amount"] is not None else 0.0
                }
                for student in students
            ]
        finally:
            cursor.close()
    finally:
        connection.close()


def get_pending_fees_students_by_name(name: str):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT s.Student_id, s.Full_name, lt.due_amount
                FROM Student AS s
                LEFT JOIN Last_Payment AS lt ON s.Last_Pay_id = lt.last_Payment_id
                WHERE (lt.due_amount > 0 OR s.Last_Pay_id IS NULL) 
                  AND s.Full_name LIKE %s
            """, (f"%{name}%",))

            students = cursor.fetchall()

            return [
                {
                    "id": student["Student_id"],
                    "name": student["Full_name"].strip(),
                    "fees_pending": float(student["due_amount"]) if student["due_amount"] is not None else 0.0
                }
                for student in students
            ]
        finally:
            cursor.close()
    finally:
        connection.close()


def get_total_fees_pending_siblings(student_id: int):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT Parent_id FROM Student WHERE Student_id = %s", (student_id,))
            parent_result = cursor.fetchone()

            if not parent_result or not parent_result["Parent_id"]:
                cursor.execute("""
                    SELECT s.Student_id, lt.due_amount 
                    FROM Student AS s 
                    LEFT JOIN Last_Payment AS lt ON s.Last_Pay_id = lt.last_Payment_id 
                    WHERE s.Student_id = %s 
                """, (student_id,))
                result = cursor.fetchone()
                return float(result["due_amount"]) if result and result["due_amount"] is not None else 0.0

            parent_id = parent_result["Parent_id"]

            cursor.execute("""
                SELECT SUM(COALESCE(lt.due_amount, 0)) AS total_pending 
                FROM Student AS s
                LEFT JOIN Last_Payment AS lt ON s.Last_Pay_id = lt.last_Payment_id
                WHERE s.Parent_id = %s
            """, (parent_id,))

            sum_result = cursor.fetchone()
            return float(sum_result["total_pending"]) if sum_result and sum_result["total_pending"] is not None else 0.0
        finally:
            cursor.close()
    finally:
        connection.close()


def get_last_kth_payment(student_id: int, k: int):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT * FROM Fees_Payment 
                WHERE Student_id = %s 
                ORDER BY Payment_date DESC 
                LIMIT 1 OFFSET %s
            """, (student_id, max(0, k - 1)))

            payment = cursor.fetchone()
            return payment if payment else None
        finally:
            cursor.close()
    finally:
        connection.close()


def get_total_collected_in_month(month_name: str, year: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT 
                SUM(amount_paid) AS total_collection,
                COUNT(Payment_id) AS total_transactions
            FROM Fees_Payment 
            WHERE For_month = %s AND For_year = %s
        """
        cursor.execute(query, (month_name, year))
        result = cursor.fetchone()

        total_amount = float(result["total_collection"]) if result["total_collection"] is not None else 0.0
        total_count = result["total_transactions"] or 0

        return {
            "month": month_name,
            "year": year,
            "total_received_rupees": total_amount,
            "total_payments_count": total_count
        }
    except Exception as e:
        print(f"Error fetching monthly collection: {e}")
        return {"month": month_name, "year": year, "total_received_rupees": 0.0, "total_payments_count": 0}
    finally:
        cursor.close()
        connection.close()


def get_unpaid_students_this_month():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    current_month = datetime.now().strftime('%B')
    current_year = datetime.now().year

    try:
        query = """
            SELECT 
                s.Student_id,
                s.Full_name,
                s.Monthly_fee_amount,
                COALESCE(lp.due_amount, s.Monthly_fee_amount) AS pending_due,
                p.Father_name,
                p.Primary_Phone
            FROM Student s
            LEFT JOIN Parent p ON s.Parent_id = p.Parent_id
            LEFT JOIN Last_Payment lp ON s.Last_Pay_id = lp.last_Payment_id
            WHERE s.Status = 'Active'
              AND (
                  s.Student_id NOT IN (
                      SELECT DISTINCT Student_id 
                      FROM Fees_Payment 
                      WHERE For_month = %s AND For_year = %s
                  )
                  OR COALESCE(lp.due_amount, 0) > 0
              )
            ORDER BY s.Student_id ASC
        """
        cursor.execute(query, (current_month, current_year))
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching unpaid students: {e}")
        return []
    finally:
        cursor.close()
        connection.close()


def get_student_overall_fee_history(student_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        student_query = """
            SELECT 
                s.Student_id,
                s.Full_name AS student_name,
                s.Monthly_fee_amount,
                p.Father_name,
                p.Primary_Phone,
                COALESCE(lp.due_amount, 0.0) AS current_due_amount
            FROM Student s
            LEFT JOIN Parent p ON s.Parent_id = p.Parent_id
            LEFT JOIN Last_Payment lp ON s.Last_Pay_id = lp.last_Payment_id
            WHERE s.Student_id = %s
        """
        cursor.execute(student_query, (student_id,))
        student_info = cursor.fetchone()

        if not student_info:
            return None

        payments_query = """
            SELECT 
                Payment_id, For_month, For_year, amount_paid, Payment_date, Payment_mode, Remark
            FROM Fees_Payment
            WHERE Student_id = %s
            ORDER BY Payment_date DESC, Payment_id DESC
        """
        cursor.execute(payments_query, (student_id,))
        payment_history = cursor.fetchall()

        total_paid_so_far = sum(float(row["amount_paid"]) for row in payment_history)

        return {
            "student_id": student_info["Student_id"],
            "student_name": student_info["student_name"].strip(),
            "father_name": student_info["Father_name"] or "N/A",
            "phone_number": student_info["Primary_Phone"] or "N/A",
            "monthly_fee_rate": float(student_info["Monthly_fee_amount"]),
            "current_due_amount": float(student_info["current_due_amount"]),
            "total_amount_paid_till_date": total_paid_so_far,
            "total_transactions_count": len(payment_history),
            "payment_history": payment_history
        }
    except Exception as e:
        print(f"Error fetching overall student fee detail: {e}")
        return None
    finally:
        cursor.close()
        connection.close()


# -------------------------------------------------------------
# 2. WRITE / TRANSACTION FUNCTIONS
# -------------------------------------------------------------

def process_fees_payment(student_id: int, paid_amount: float, payment_mode: str = "Cash"):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    current_date = datetime.now().strftime('%Y-%m-%d')
    current_month = datetime.now().strftime('%B')
    current_year = datetime.now().year

    try:
        connection.start_transaction()

        cursor.execute("SELECT Parent_id FROM Student WHERE Student_id = %s", (student_id,))
        student_data = cursor.fetchone()

        if not student_data:
            return {"status": False, "message": "Student not found"}

        parent_id = student_data.get("Parent_id")

        if parent_id:
            cursor.execute("""
                SELECT Student_id, Monthly_fee_amount, Last_Pay_id 
                FROM Student 
                WHERE Parent_id = %s 
                ORDER BY Student_id ASC
            """, (parent_id,))
            family_students = cursor.fetchall()
        else:
            cursor.execute("""
                SELECT Student_id, Monthly_fee_amount, Last_Pay_id 
                FROM Student 
                WHERE Student_id = %s
            """, (student_id,))
            family_students = cursor.fetchall()

        num_students = len(family_students)
        students_info = []
        total_family_due = 0.0

        for st in family_students:
            sid = st["Student_id"]
            last_pay_id = st["Last_Pay_id"]

            if last_pay_id:
                cursor.execute("SELECT due_amount FROM Last_Payment WHERE last_Payment_id = %s", (last_pay_id,))
                lp_res = cursor.fetchone()
                current_due = float(lp_res["due_amount"]) if lp_res and lp_res["due_amount"] is not None else 0.0
            else:
                current_due = float(st["Monthly_fee_amount"])

            students_info.append({
                "student_id": sid,
                "monthly_fee": float(st["Monthly_fee_amount"]),
                "old_due": current_due
            })
            total_family_due += current_due

        cursor.execute("""
            INSERT INTO Transaction (Student_id, Parent_id, Paid_amount, PaymentList_id, month)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, parent_id, paid_amount, json.dumps([]), current_month))

        transaction_id = cursor.lastrowid
        net_remaining_family_due = total_family_due - paid_amount

        if net_remaining_family_due <= 0:
            individual_new_due = 0.0
            extra_advance = abs(net_remaining_family_due)
        else:
            individual_new_due = net_remaining_family_due / num_students
            extra_advance = 0.0

        created_payment_ids = []

        for st in students_info:
            sid = st["student_id"]
            old_due = st["old_due"]
            actual_paid_for_student = max(0.0, old_due - individual_new_due)

            cursor.execute("""
                INSERT INTO Fees_Payment (Student_id, For_month, For_year, amount_paid, Payment_date, Payment_mode, Remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (sid, current_month, current_year, actual_paid_for_student, current_date, payment_mode, f"Fees Payment for {current_month} {current_year}"))

            pay_id = cursor.lastrowid
            created_payment_ids.append(pay_id)

            cursor.execute("""
                INSERT INTO Last_Payment (transaction_id, due_amount, Remarks)
                VALUES (%s, %s, %s)
            """, (transaction_id, individual_new_due, f"Updated after Txn #{transaction_id}"))

            new_last_pay_id = cursor.lastrowid

            cursor.execute("""
                UPDATE Student SET Last_Pay_id = %s WHERE Student_id = %s
            """, (new_last_pay_id, sid))

        cursor.execute("""
            UPDATE Transaction 
            SET PaymentList_id = %s 
            WHERE transaction_id = %s
        """, (json.dumps(created_payment_ids), transaction_id))

        connection.commit()

        return {
            "status": True,
            "transaction_id": transaction_id,
            "new_due_per_student": individual_new_due,
            "extra_advance": extra_advance
        }

    except Exception as e:
        connection.rollback()
        print(f"Transaction failed: {e}")
        return {"status": False, "error": str(e)}
    finally:
        cursor.close()
        connection.close()


def create_new_student(
    full_name: str,
    monthly_fee_amount: float,
    gender: str = 'Male',
    class_grade: str = None,
    school_name: str = None,
    joining_date: str = None,
    parent_id: int = None,
    father_name: str = None,
    primary_phone: str = None,
    address: str = None
):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    current_date = datetime.now().strftime('%Y-%m-%d')

    try:
        connection.start_transaction()

        if not parent_id and primary_phone:
            cursor.execute("""
                INSERT INTO Parent (Father_name, Primary_Phone, Address)
                VALUES (%s, %s, %s)
            """, (father_name, primary_phone, address))
            parent_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO Student (
                Full_name, gender, class_grade, School_name, Joining_date, 
                Monthly_fee_amount, Parent_id, Status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active')
        """, (full_name, gender, class_grade, school_name, joining_date or current_date, monthly_fee_amount, parent_id))

        new_student_id = cursor.lastrowid

        # Dummy transaction to link initial Last_Payment row since transaction_id is NOT NULL in schema
        cursor.execute("""
            INSERT INTO Transaction (Student_id, Parent_id, Paid_amount, PaymentList_id, month)
            VALUES (%s, %s, 0.00, %s, %s)
        """, (new_student_id, parent_id, json.dumps([]), datetime.now().strftime('%B')))

        initial_txn_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO Last_Payment (transaction_id, due_amount, Remarks)
            VALUES (%s, %s, %s)
        """, (initial_txn_id, monthly_fee_amount, f"Initial due setup on registration {current_date}"))

        last_pay_id = cursor.lastrowid

        cursor.execute("""
            UPDATE Student SET Last_Pay_id = %s WHERE Student_id = %s
        """, (last_pay_id, new_student_id))

        connection.commit()

        return {
            "status": True,
            "student_id": new_student_id,
            "parent_id": parent_id,
            "monthly_fee_amount": monthly_fee_amount,
            "initial_due": monthly_fee_amount
        }

    except Exception as e:
        connection.rollback()
        print(f"Error creating student: {e}")
        return {"status": False, "error": str(e)}
    finally:
        cursor.close()
        connection.close()


def deactivate_student(student_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute("SELECT Student_id, Full_name, Status FROM Student WHERE Student_id = %s", (student_id,))
        student = cursor.fetchone()

        if not student:
            return {"status": False, "message": f"Student ID {student_id} not found."}

        if student["Status"] == "Inactive":
            return {"status": True, "message": f"Student ID {student_id} is already inactive."}

        cursor.execute("UPDATE Student SET Status = 'Inactive' WHERE Student_id = %s", (student_id,))
        connection.commit()

        return {"status": True, "student_id": student_id, "new_status": "Inactive"}

    except Exception as e:
        connection.rollback()
        print(f"Error deactivating student: {e}")
        return {"status": False, "error": str(e)}
    finally:
        cursor.close()
        connection.close()


def hard_delete_student(student_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute("SELECT Student_id, Last_Pay_id FROM Student WHERE Student_id = %s", (student_id,))
        student = cursor.fetchone()

        if not student:
            return {"status": False, "message": f"Student ID {student_id} not found."}

        last_pay_id = student.get("Last_Pay_id")

        cursor.execute("UPDATE Student SET Last_Pay_id = NULL WHERE Student_id = %s", (student_id,))
        cursor.execute("DELETE FROM Fees_Payment WHERE Student_id = %s", (student_id,))
        cursor.execute("DELETE FROM Attendance WHERE Student_id = %s", (student_id,))
        cursor.execute("DELETE FROM Transaction WHERE Student_id = %s", (student_id,))

        if last_pay_id:
            cursor.execute("DELETE FROM Last_Payment WHERE last_Payment_id = %s", (last_pay_id,))

        cursor.execute("DELETE FROM Student WHERE Student_id = %s", (student_id,))
        connection.commit()

        return {"status": True, "message": f"Student ID {student_id} permanently deleted."}

    except Exception as e:
        connection.rollback()
        print(f"Error hard deleting student: {e}")
        return {"status": False, "error": str(e)}
    finally:
        cursor.close()
        connection.close()
        
        
        
def filter_students_by_name(search_name: str):
    
    
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            query = """
                SELECT 
                    s.Student_id,
                    s.Full_name,
                    s.gender,
                    s.class_grade,
                    s.School_name,
                    s.Monthly_fee_amount,
                    s.Status,
                    p.Father_name,
                    p.Primary_Phone
                FROM Student s
                LEFT JOIN Parent p ON s.Parent_id = p.Parent_id
                WHERE s.Full_name LIKE %s
            """
            # Wildcards (%) ko python parameter me add karte hain
            search_pattern = f"%{search_name}%"
            cursor.execute(query, (search_pattern,))
            
            return cursor.fetchall()
        finally:
            cursor.close()
    finally:
        connection.close()
        
        
def filter_students_by_class(class_name: str):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            query = """
                SELECT 
                    s.Student_id,
                    s.Full_name,
                    s.gender,
                    s.class_grade,
                    s.School_name,
                    s.Monthly_fee_amount,
                    s.Status,
                    p.Father_name,
                    p.Primary_Phone
                FROM Student s
                LEFT JOIN Parent p ON s.Parent_id = p.Parent_id
                WHERE s.class_grade = %s
                ORDER BY s.Full_name ASC
            """
            cursor.execute(query, (class_name,))
            return cursor.fetchall()
        finally:
            cursor.close()
    finally:
        connection.close()



def create_new_multiple_students(
    father_name: str,
    mother_name: str,
    primary_phone: str,
    address: str,
    students_list: list
):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    current_date = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%B")

    try:
        # -----------------------------
        # Validation
        # -----------------------------

        if not students_list:
            return {
                "status": "error",
                "message": "At least one student is required."
            }

        if not father_name:
            return {
                "status": "error",
                "message": "Father name is required."
            }

        if not primary_phone:
            return {
                "status": "error",
                "message": "Primary phone is required."
            }

        # -----------------------------
        # Start transaction
        # -----------------------------

        connection.start_transaction()

        # -----------------------------
        # Create Parent
        # -----------------------------

        cursor.execute(
            """
            INSERT INTO Parent
            (
                Father_name,
                Mother_name,
                Primary_Phone,
                Address
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                father_name,
                mother_name,
                primary_phone,
                address
            )
        )

        parent_id = cursor.lastrowid

        created_students = []

        # -----------------------------
        # Create Students
        # -----------------------------

        for student in students_list:

            full_name = student.get("full_name")
            monthly_fee_amount = student.get(
                "monthly_fee_amount"
            )
            gender = student.get(
                "gender",
                "Male"
            )
            class_grade = student.get(
                "class_grade"
            )
            school_name = student.get(
                "school_name"
            )
            joining_date = student.get(
                "joining_date",
                current_date
            )

            # Validation
            if not full_name:
                raise ValueError(
                    "Student full_name is required."
                )

            if monthly_fee_amount is None:
                raise ValueError(
                    f"Monthly fee is required for {full_name}."
                )

            # -----------------------------
            # Student
            # -----------------------------

            cursor.execute(
                """
                INSERT INTO Student
                (
                    Full_name,
                    gender,
                    class_grade,
                    School_name,
                    Joining_date,
                    Monthly_fee_amount,
                    Parent_id,
                    Status
                )
                VALUES
                (
                    %s, %s, %s, %s,
                    %s, %s, %s, 'Active'
                )
                """,
                (
                    full_name,
                    gender,
                    class_grade,
                    school_name,
                    joining_date,
                    monthly_fee_amount,
                    parent_id
                )
            )

            student_id = cursor.lastrowid

            # -----------------------------
            # Initial Transaction
            # -----------------------------

            cursor.execute(
                """
                INSERT INTO Transaction
                (
                    Student_id,
                    Parent_id,
                    Paid_amount,
                    PaymentList_id,
                    month
                )
                VALUES
                (
                    %s, %s, %s, %s, %s
                )
                """,
                (
                    student_id,
                    parent_id,
                    0.00,
                    json.dumps([]),
                    current_month
                )
            )

            transaction_id = cursor.lastrowid

            # -----------------------------
            # Last Payment / Due
            # -----------------------------

            cursor.execute(
                """
                INSERT INTO Last_Payment
                (
                    transaction_id,
                    due_amount,
                    Remarks
                )
                VALUES
                (
                    %s, %s, %s
                )
                """,
                (
                    transaction_id,
                    monthly_fee_amount,
                    f"Initial due setup on registration {current_date}"
                )
            )

            last_payment_id = cursor.lastrowid

            # -----------------------------
            # Link Last Payment to Student
            # -----------------------------

            cursor.execute(
                """
                UPDATE Student
                SET Last_Pay_id = %s
                WHERE Student_id = %s
                """,
                (
                    last_payment_id,
                    student_id
                )
            )

            # -----------------------------
            # Store Created Student
            # -----------------------------

            created_students.append({
                "student_id": student_id,
                "full_name": full_name,
                "gender": gender,
                "class_grade": class_grade,
                "school_name": school_name,
                "joining_date": str(joining_date),
                "monthly_fee_amount": monthly_fee_amount,
                "parent_id": parent_id,
                "status": "Active",
                "last_payment_id": last_payment_id,
                "due_amount": monthly_fee_amount
            })

        # -----------------------------
        # Commit
        # -----------------------------

        connection.commit()

        return {
            "status": "success",
            "message": (
                f"{len(created_students)} student(s) "
                "created successfully."
            ),
            "parent": {
                "parent_id": parent_id,
                "father_name": father_name,
                "mother_name": mother_name,
                "primary_phone": primary_phone,
                "address": address
            },
            "students": created_students
        }

    except Exception as e:

        # -----------------------------
        # Rollback
        # -----------------------------

        connection.rollback()

        return {
            "status": "error",
            "message": str(e)
        }

    finally:

        cursor.close()
        connection.close()
        
        
# ============================================================
# CHAT SESSION FUNCTIONS
# ============================================================

def create_chat_session():
    """
    Create a new chat session and return session_id.
    """

    session_id = str(uuid.uuid4())

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO chat_sessions
            (session_id, title, messages)
            VALUES (%s, %s, %s)
            """,
            (
                session_id,
                "New Chat",
                json.dumps([])
            )
        )

        connection.commit()

        return session_id

    finally:
        cursor.close()
        connection.close()


def get_chat_sessions():
    """
    Get all previous chat sessions.
    Used for the chat history sidebar.
    """

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                session_id,
                title,
                created_at,
                updated_at
            FROM chat_sessions
            ORDER BY updated_at DESC
            """
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


def get_chat_session(session_id):
    """
    Get one complete chat session.
    """

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                session_id,
                title,
                messages,
                created_at,
                updated_at
            FROM chat_sessions
            WHERE session_id = %s
            """,
            (session_id,)
        )

        result = cursor.fetchone()

        if not result:
            return None

        # MySQL JSON can come as string depending on connector
        if isinstance(result["messages"], str):
            result["messages"] = json.loads(result["messages"])

        return result

    finally:
        cursor.close()
        connection.close()


def save_chat_message(
    session_id: str,
    user_message: str,
    ai_message: str
):
    """
    Add user and AI messages to an existing session.
    """

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # Get current messages
        cursor.execute(
            """
            SELECT messages
            FROM chat_sessions
            WHERE session_id = %s
            """,
            (session_id,)
        )

        result = cursor.fetchone()

        if not result:
            raise ValueError("Chat session not found")

        messages = result["messages"]

        if isinstance(messages, str):
            messages = json.loads(messages)

        # ----------------------------------------------------
        # Add user message
        # ----------------------------------------------------

        messages.append({
            "role": "user",
            "content": user_message
        })

        # ----------------------------------------------------
        # Add AI message
        # ----------------------------------------------------

        messages.append({
            "role": "assistant",
            "content": ai_message
        })

        # ----------------------------------------------------
        # Generate title from first user message
        # ----------------------------------------------------

        title = user_message.strip()

        if len(title) > 50:
            title = title[:50] + "..."

        # ----------------------------------------------------
        # Update database
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE chat_sessions
            SET
                messages = %s,
                title = CASE
                    WHEN title = 'New Chat'
                    THEN %s
                    ELSE title
                END,
                updated_at = CURRENT_TIMESTAMP
            WHERE session_id = %s
            """,
            (
                json.dumps(messages),
                title,
                session_id
            )
        )

        connection.commit()

        return messages

    finally:
        cursor.close()
        connection.close()