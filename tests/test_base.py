from fastapi import status
from services.config import settings

def test_first_launch_redirects_to_initial_setup_when_db_is_empty(client, test_db):

    cursor = test_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM users;")
    user_count = cursor.fetchone()[0]
    assert user_count == 0
    
    """Verifies that the real routing logic catches an empty system state."""
    # Act: Request the real dashboard route
    response = client.get("/login", follow_redirects=False)
    # Assert: Your real logic correctly detects 0 users and redirects
    
    assert response.status_code == 303
    assert response.headers.get("location") == "/initial-setup"

def test_incorrect_authorization_for_initial_setup(client, test_db):

    cursor = test_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM users;")
    user_count = cursor.fetchone()[0]
    assert user_count == 0
    
    form_data = {
        "master_app_key": "wrong-security-key-123", 
        "username": "bad_admin",
        "email": "hacker@domain.com",
        "password": "SecurePassword99!"
    }
    response = client.post("/initial-setup", data=form_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    cursor.execute("SELECT COUNT(*) FROM users;")
    assert cursor.fetchone()[0] == 0

def test_correct_authorization_and_hashing_for_initial_setup(client, test_db):

    cursor = test_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM users;")
    user_count = cursor.fetchone()[0]
    assert user_count == 0
    
    form_data = {
        "master_app_key": f"{settings.SECRET_KEY}", 
        "username": "admin",
        "email": "admin@company.com",
        "password": "SecureAuthorizedPassword99!"
    }
    response = client.post("/initial-setup", data=form_data)
    assert response.status_code == 200
    
    cursor.execute("SELECT COUNT(*) FROM users;")
    assert cursor.fetchone()[0] == 1

    cursor.execute("SELECT hashed_password FROM users WHERE username = 'admin'")
    password = cursor.fetchone()[0]
    assert password != "SecureAuthorizedPassword99!"

def test_login_flow_with_existing_admin_user(client, seeded_admin_db):

    # First, we test a login with incorrect credentials (username AND password)

    form_data = {
        "username": "Admin",
        "password": "TestAdminPassword555"
    }
    response = client.post("/login", data=form_data)
    assert "Invalid credentials" in response.text

    # Now, we test a login with the correct credentials
    form_data = {
        "username": "seeded_admin",
        "password": "TestAdminPassword555!"
    }
    response = client.post("/login", data=form_data)
    assert response.status_code == 200
    assert "Dashboard" in response.text
    username = 'seeded_admin'
    cursor = seeded_admin_db.cursor()

    # Verify that a session is created
    cursor.execute(
            """
            SELECT id, session_token, user_id, email, username, permissions, is_active, created_at
            FROM sessions
            WHERE username = ? AND is_active = 1
            """,
            (username,)
        )
    row = cursor.fetchone()
    assert row is not None
    session_token, user_id, email, username, permissions, is_active, created_at = row[1], row[2], row[3], row[4], row[5], row[6], row[7]
    assert session_token is not None
    assert user_id is not None
    assert email == 'seeded@spine.com'
    assert username == 'seeded_admin'
    assert permissions == 'Admin'
    assert is_active == 1
    assert created_at is not None

    # Log out
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code in (status.HTTP_302_FOUND, status.HTTP_303_SEE_OTHER)
    assert "/login" in response.headers.get("location", "")

def test_logout_invalidates_session_and_blocks_dashboard(client, authenticated_admin_client, test_db):
    response = authenticated_admin_client.get("/logout", follow_redirects=False)
    assert response.status_code in (status.HTTP_302_FOUND, status.HTTP_303_SEE_OTHER)
    assert "/login" in response.headers.get("location", "")

    cursor = test_db.cursor()
    cursor.execute(
        """
        SELECT is_active, revoked_at 
        FROM sessions 
        WHERE session_token = ?;
        """, 
        ("mock-test-session-uuid-1234",)
    )
    row = cursor.fetchone()
    
    
    assert row is not None
    is_active, revoked_at = row[0], row[1]
    
    # Verify session is revoked in database
    assert is_active == 0
    assert revoked_at is not None 

    # Ensure that dashboard is blocked when logged out
    dash_response = authenticated_admin_client.get("/dashboard", follow_redirects=False)
    assert dash_response.status_code in (status.HTTP_302_FOUND, status.HTTP_303_SEE_OTHER)
    assert "/login" in dash_response.headers.get("location", "")

def test_create_standard_user_as_admin(client, authenticated_admin_client, test_db):
   
    form_data = {
        "username": "m_smith",
        "email": "msmith@example.com",
        "permission": "User",       
        "password": "SecureUserPassword789!"
    }
   
    response = authenticated_admin_client.post(
        "/dashboard/users/create", 
        data=form_data, 
        follow_redirects=False
    )
   
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER)
    cursor = test_db.cursor()
    cursor.execute(
        """
        SELECT email, permissions, hashed_password 
        FROM users 
        WHERE username = ?;
        """, 
        ("m_smith",)
    )
    user_record = cursor.fetchone()

    assert user_record is not None
    email, permissions, hashed_password = user_record[0], user_record[1], user_record[2]

    
    assert email == "msmith@example.com"
    assert permissions == "User"
    assert hashed_password != "SecureUserPassword789!"

def test_login_flow_with_existing_standard_user(client, seeded_standard_user_db):

    # First, we test a login with incorrect credentials (username AND password)

    form_data = {
        "username": "standard_user",
        "password": "TestStandardUserPassword555"
    }
    response = client.post("/login", data=form_data)
    assert "Invalid credentials" in response.text

    # Now, we test a login with the correct credentials
    form_data = {
        "username": "standard_user",
        "password": "TestStandardUserPassword555!"
    }
    response = client.post("/login", data=form_data)
    assert response.status_code == 200
    assert "Dashboard" in response.text
    username = 'standard_user'
    cursor = seeded_standard_user_db.cursor()

    # Verify that a session is created
    cursor.execute(
            """
            SELECT id, session_token, user_id, email, username, permissions, is_active, created_at
            FROM sessions
            WHERE username = ? AND is_active = 1
            """,
            (username,)
        )
    row = cursor.fetchone()
    assert row is not None
    session_token, user_id, email, username, permissions, is_active, created_at = row[1], row[2], row[3], row[4], row[5], row[6], row[7]
    assert session_token is not None
    assert user_id is not None
    assert email == 'standard@spine.com'
    assert username == 'standard_user'
    assert permissions == 'User'
    assert is_active == 1
    assert created_at is not None

    # Now we do something different, we check if the frontend displays the right content for this permission level
    assert "Sessions" not in response.text
    assert "Users" not in response.text

    # Log out
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code in (status.HTTP_302_FOUND, status.HTTP_303_SEE_OTHER)
    assert "/login" in response.headers.get("location", "")

def test_admin_revoking_session_terminates_session_and_sends_user_back_to_login_page(
    client, 
    authenticated_admin_client, 
    authenticated_standard_client, 
    test_db
):
   cursor = test_db.cursor()
   mock_standard_token = "mock-standard-session-uuid-5678"
   session_row = cursor.execute(
            "SELECT id, is_active FROM sessions WHERE session_token = ?;",
            (mock_standard_token,)
        ).fetchone()
   
   assert session_row is not None
   is_active = session_row[1]

   assert session_row[0]is not None
   standard_session_id = session_row[0]

   assert is_active == 1

   revoke_url = f"/dashboard/revoke-session/{standard_session_id}"
   mock_admin_token = "mock-test-session-uuid-1234"
   authenticated_admin_client.cookies.set("session_token", mock_admin_token)
   admin_response = authenticated_admin_client.post(revoke_url, follow_redirects=False)
   assert admin_response.status_code == 200

   updated_row = cursor.execute(
        "SELECT is_active, revoked_at FROM sessions WHERE id = ?;",
        (standard_session_id,)
        ).fetchone()
    
   assert updated_row is not None
   updated_is_active = updated_row[0]
   revoked_at = updated_row[1]
   assert updated_is_active == 0
   assert revoked_at is not None

   # Swap back cookies to standard client cookie
   authenticated_standard_client.cookies.set("session_token", mock_standard_token)
   standard_response = authenticated_standard_client.get("/dashboard", follow_redirects=False)
    
   # Assert they are aggressively caught and redirected back out to safety
   assert standard_response.status_code in (status.HTTP_302_FOUND, status.HTTP_303_SEE_OTHER)
   assert "/login" in standard_response.headers.get("location", "")

def test_delete_standard_user_as_admin(
    client, 
    authenticated_admin_client, 
    authenticated_standard_client, 
    test_db
):
    """
    Verifies that an administrator can delete a standard user account,
    the user and their associated sessions are removed from the database,
    and the deleted user can no longer access protected endpoints.
    """
    cursor = test_db.cursor()
    
    # Target values from your standard user fixture setup
    mock_standard_token = "mock-standard-session-uuid-5678"
    mock_standard_user_id = "fake-standard-user-id-999"
    mock_admin_token = "mock-test-session-uuid-1234"

    # -------------------------------------------------------------------------
    # STEP 1: Verify Preconditions
    # -------------------------------------------------------------------------
    # Ensure the standard user and their session exist before running the test
    cursor.execute("SELECT COUNT(*) FROM users WHERE id = ?;", (mock_standard_user_id,))
    assert cursor.fetchone()[0] == 1
    
    cursor.execute("SELECT COUNT(*) FROM sessions WHERE session_token = ?;", (mock_standard_token,))
    assert cursor.fetchone()[0] == 1

    # -------------------------------------------------------------------------
    # STEP 2: Issue Delete Request as Admin
    # -------------------------------------------------------------------------
    # Fix the cookie jar to make sure the Admin is driving
    authenticated_admin_client.cookies.set("session_token", mock_admin_token)
    
    # Assuming your route follows a RESTful pattern or HTMX layout like /dashboard/users/delete/{id}
    delete_url = f"/dashboard/users/delete/{mock_standard_user_id}"
    response = authenticated_admin_client.delete(delete_url, follow_redirects=False)
    
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER)

    # -------------------------------------------------------------------------
    # STEP 3: Verify Database Cascades/Deletions
    # -------------------------------------------------------------------------
    # The user should be gone
    cursor.execute("SELECT COUNT(*) FROM users WHERE id = ?;", (mock_standard_user_id,))
    assert cursor.fetchone()[0] == 0
    
    # Because of ON DELETE CASCADE in your schema, their active session should be completely wiped too
    cursor.execute("SELECT COUNT(*) FROM sessions WHERE session_token = ?;", (mock_standard_token,))
    assert cursor.fetchone()[0] == 0

    # -------------------------------------------------------------------------
    # STEP 4: Verify the Deleted User is Blocked
    # -------------------------------------------------------------------------
    # Flip the cookie jar back to the standard user's old token
    authenticated_standard_client.cookies.set("session_token", mock_standard_token)
    
    # Any attempt by the dead session/user to request data must bounce them out to login
    standard_response = authenticated_standard_client.get("/dashboard", follow_redirects=False)
    assert standard_response.status_code in (status.HTTP_302_FOUND, status.HTTP_303_SEE_OTHER)
    assert "/login" in standard_response.headers.get("location", "")

def test_edit_standard_user_as_admin( 
    client,
    authenticated_admin_client,
    authenticated_standard_client,
    test_db
):
    """
    Verifies that an administrator can modify a standard user's account profiles 
    (e.g., username, email, or permissions), and that the changes correctly save to the database.
    """
    cursor = test_db.cursor()
    
    # Target values from your fixtures setup
    mock_standard_user_id = "fake-standard-user-id-999"
    mock_standard_token = "mock-standard-session-uuid-5678"
    mock_admin_token = "mock-test-session-uuid-1234"

    # -------------------------------------------------------------------------
    # STEP 1: Define Form Modification Payload
    # -------------------------------------------------------------------------
    # Imagine this is an admin dashboard editing form where we change the standard 
    # user's username, email suffix, and elevate their role to Admin.
    form_payload = {
        "username": "m_smith_updated",
        "email": "msmith_new@spine.com",
        "permissions": "Admin"  
    }

    # -------------------------------------------------------------------------
    # STEP 2: Issue Edit Request as Admin
    # -------------------------------------------------------------------------
    # Secure the cookie jar so the Admin is executing the request
    
    authenticated_admin_client.cookies.set("session_token", mock_admin_token)
    
    # Assuming your update endpoint matches a pattern like /dashboard/users/edit/{id}
    headers = {"HX-Request": "true"}
    
    edit_url = f"/dashboard/users/update/{mock_standard_user_id}"

    response = authenticated_admin_client.put(
        edit_url, 
        data=form_payload, 
        headers=headers, 
        follow_redirects=False
    )
    
    # Expect success (either HTMX 200 OK swap or a post-save redirect)
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER)

    # Flush the SQLite memory cache lines to disk
    test_db.commit()

    # -------------------------------------------------------------------------
    # STEP 3: Verify Modifications in the Database
    # -------------------------------------------------------------------------
    cursor.execute(
        """
        SELECT username, email, permissions 
        FROM users 
        WHERE id = ?;
        """, 
        (mock_standard_user_id,)
    )
    updated_user = cursor.fetchone()

    assert updated_user is not None
    username, email, permissions = updated_user[0], updated_user[1], updated_user[2]

    # Confirm the values match our submitted modification data
    assert username == "m_smith_updated"
    assert email == "msmith_new@spine.com"
    assert permissions == "Admin"


    authenticated_standard_client.cookies.set("session_token", mock_standard_token)
    
    # 2. Request the dashboard layout as the updated user
    dash_response = authenticated_standard_client.get("/dashboard", follow_redirects=True)
    assert dash_response.status_code == status.HTTP_200_OK
    
    # 3. Assert that they can now see the privileged interface strings 
    # (reversing the check from your standard user login flow test)
    assert "Sessions" in dash_response.text
    assert "Users" in dash_response.text

def test_accessing_locked_routes_as_standard_user_returns_forbidden( 
    client,
    test_db
):
    """
    Creates a brand-new standard user to act as the attacker, and forces
    them to attempt administrative actions (Create, Edit View, Update, Delete) to
    verify they are blocked at both the HTTP level and database level.
    """
    cursor = test_db.cursor()
    
    # -------------------------------------------------------------------------
    # STEP 1: Set up the attacker (A pristine Standard User & Session)
    # -------------------------------------------------------------------------
    valid_regular_id = "real-isolated-user-123"
    valid_regular_token = "isolated-token-xyz"
    
    cursor.execute(
        """
        INSERT INTO users (id, email, username, permissions, hashed_password) 
        VALUES (?, 'isolated@spine.com', 'isolated_user', 'User', 'hash');
        """,
        (valid_regular_id,)
    )
    cursor.execute(
        """
        INSERT INTO sessions (session_token, user_id, email, username, permissions, is_active) 
        VALUES (?, ?, 'isolated@spine.com', 'isolated_user', 'User', 1);
        """,
        (valid_regular_token, valid_regular_id)
    )
    test_db.commit()

    # Wire up our standard user's cookie context
    client.cookies.set("session_token", valid_regular_token)

    # -------------------------------------------------------------------------
    # STEP 2: Define the Attack Payloads
    # -------------------------------------------------------------------------
    dummy_user_form = {
        "username": "hacker_compromise", 
        "email": "hacker@spine.com", 
        "permissions": "Admin"
    }

    admin_only_endpoints = [
        # 1. Attempting to CREATE a new user
        ("/dashboard/users/create", "POST", dummy_user_form),
        
        # 2. Attempting to access the EDIT interface page/form view (GET)
        (f"/dashboard/users/edit/{valid_regular_id}", "GET", None),
        
        # 3. Attempting to execute an UPDATE modification (PUT)
        (f"/dashboard/users/update/{valid_regular_id}", "PUT", dummy_user_form),
        
        # 4. Attempting to execute a DELETE action
        (f"/dashboard/users/delete/{valid_regular_id}", "DELETE", None),
    ]

    # -------------------------------------------------------------------------
    # STEP 3: Execute the Attack Loop & Verify Constraints
    # -------------------------------------------------------------------------
    for url, method, payload in admin_only_endpoints:
        data_payload = payload if payload is not None else {}
        
        if method == "POST":
            response = client.post(url, data=data_payload, follow_redirects=False)
        elif method == "GET":
            response = client.get(url, follow_redirects=False)
        elif method == "PUT":
            response = client.put(url, data=data_payload, follow_redirects=False)
        elif method == "DELETE":
            response = client.delete(url, follow_redirects=False)

        # Force SQLite transaction logs to flush
        test_db.commit()

        # Look up the status of our original setup user after the attack
        user_record = cursor.execute(
            "SELECT username, permissions FROM users WHERE id = ?;", 
            (valid_regular_id,)
        ).fetchone()

        # Check total user count to catch unauthorized creations
        total_users = cursor.execute("SELECT COUNT(*) FROM users;").fetchone()[0]

        # --- DATABASE INTEGRITY ASSERTIONS ---
        if method == "POST":
            # If the gate failed, total_users would be 2
            assert total_users == 1, f"Security Breach: {method} {url} allowed an unauthorized user to CREATE a record!"
        
        elif method in ("GET", "PUT"):
            # Ensure the user profile wasn't mutated or wiped during the edit view/update attempts
            assert user_record is not None, f"User went missing during {method} loop check."
            assert user_record[0] == "isolated_user", f"Security Breach: {method} {url} allowed an unauthorized user to alter a record!"
        
        elif method == "DELETE":
            # If the gate failed, the row would be completely gone (None)
            assert user_record is not None, f"Security Breach: {method} {url} allowed an unauthorized user to DELETE a record!"

        # --- HTTP STATUS CODE ASSERTION ---
        assert response.status_code == status.HTTP_403_FORBIDDEN

def test_self_deletion_config_flag_prevents_self_deletion(
    authenticated_admin_client,
    test_db
):
    mock_admin_id = "fake-user-id-555"
    settings.USER_CAN_DELETE_SELF = False
    
    cursor = test_db.cursor()
    cursor.execute("SELECT 1 FROM users WHERE id = ?", (mock_admin_id,))
    admin_exists = cursor.fetchone() is not None
    cursor.close()
    
    assert admin_exists
    
    response = authenticated_admin_client.delete(f"/dashboard/users/delete/{mock_admin_id}", follow_redirects=False)
    assert response.status_code == 400
    
    cursor = test_db.cursor()
    cursor.execute("SELECT 1 FROM users WHERE id = ?", (mock_admin_id,))
    admin_still_exists = cursor.fetchone() is not None
    cursor.close()

    assert admin_still_exists

def test_self_deletion_config_flag_prevents_self_deletion(
    authenticated_admin_client,
    test_db
):
    mock_admin_id = "fake-user-id-555"
    settings.USER_CAN_DELETE_SELF = True
    
    cursor = test_db.cursor()
    cursor.execute("SELECT 1 FROM users WHERE id = ?", (mock_admin_id,))
    admin_exists = cursor.fetchone() is not None
    cursor.close()
    
    assert admin_exists
    
    response = authenticated_admin_client.delete(f"/dashboard/users/delete/{mock_admin_id}", follow_redirects=False)
    assert response.status_code == 200
    
    cursor = test_db.cursor()
    cursor.execute("SELECT 1 FROM users WHERE id = ?", (mock_admin_id,))
    admin_still_exists = cursor.fetchone() is not None
    cursor.close()

    assert not admin_still_exists
    response = authenticated_admin_client.delete(f"/dashboard/users/delete/{mock_admin_id}", follow_redirects=False)
    assert response.status_code in (status.HTTP_302_FOUND, status.HTTP_303_SEE_OTHER)
    assert "/login" in response.headers.get("location", "")
