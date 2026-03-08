# APEX v2 — UAT Test Guide

## Table of Contents
1. [Test Environment Setup](#1-test-environment-setup)
2. [Test Users & Personas](#2-test-users--personas)
3. [Seed Data Script](#3-seed-data-script)
4. [Module Test Cases](#4-module-test-cases)
   - [M1: Authentication](#m1-authentication)
   - [M2: Projects](#m2-projects)
   - [M3: Phases](#m3-phases)
   - [M4: Tasks](#m4-tasks)
   - [M5: Sources](#m5-sources)
   - [M6: Documents](#m6-documents)
   - [M7: Questions](#m7-questions)
   - [M8: Feedback](#m8-feedback)
   - [M9: Costs & Tracking](#m9-costs--tracking)
   - [M10: Audit Log](#m10-audit-log)
   - [M11: Notifications](#m11-notifications)
   - [M12: Improvements](#m12-improvements)
   - [M13: RBAC & Permissions](#m13-rbac--permissions)
5. [End-to-End Scenario](#5-end-to-end-scenario)
6. [Quick Reference — API Cheat Sheet](#6-quick-reference--api-cheat-sheet)

---

## 1. Test Environment Setup

```bash
# Terminal 1 — Backend
cd /Users/012runkumar/cja-accelerator/apex-v2
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 — Frontend
cd /Users/012runkumar/cja-accelerator/apex-v2/frontend
npm run dev

# URLs
# Frontend: http://localhost:3001
# Backend:  http://localhost:8001
# API Docs: http://localhost:8001/docs
```

---

## 2. Test Users & Personas

| # | User | Email | Password | Role | Project Role |
|---|------|-------|----------|------|-------------|
| 1 | APEX Admin | admin@apex.dev | admin123 | ARCHITECT | Full access (creator) |
| 2 | Sarah Chen | sarah@apex.dev | test123 | ARCHITECT | Solution Architect |
| 3 | Mike Torres | mike@apex.dev | test123 | ENGINEER | Implementation Engineer |
| 4 | Lisa Wang | lisa@client.com | test123 | CLIENT | Client Stakeholder |
| 5 | James Park | james@adobe.com | test123 | ADOBE_LAUNCH_ADVISORY | Launch Advisory |

### Permission Matrix Quick Reference

| Permission | ARCHITECT | ENGINEER | CLIENT | ADOBE_LAUNCH |
|------------|-----------|----------|--------|--------------|
| Create project | YES | NO | NO | NO |
| View all projects | YES | NO | NO | NO |
| Assign roles | YES | NO | NO | NO |
| Complete task | YES (own) | YES (own) | YES (own) | YES (own) |
| Override gate | YES | NO | NO | NO |
| View audit log | YES | NO | NO | NO |
| View costs | YES | NO | NO | NO |
| Submit feedback | YES | YES | NO | YES |
| Review improvements | YES | NO | NO | NO |
| Sign-off gate | YES | NO | YES | NO |
| Answer questions | YES | YES | YES | YES |

---

## 3. Seed Data Script

Run this script to create all test users, a sample project, and assign roles.

Save as `test_seed.sh` in project root and run: `bash test_seed.sh`

```bash
#!/bin/bash
# ============================================================
# APEX v2 — UAT Seed Script
# Creates test users, sample project, and assigns roles
# ============================================================

BASE="http://localhost:8001/api/v1"

echo "========================================="
echo "  APEX v2 UAT Seed Script"
echo "========================================="

# --- Step 1: Login as admin to get token ---
echo -e "\n[1/7] Logging in as admin..."
AUTH=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@apex.dev&password=admin123")
TOKEN=$(echo $AUTH | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
AUTH_HEADER="Authorization: Bearer $TOKEN"
echo "  Token obtained."

# --- Step 2: Get org ID ---
echo -e "\n[2/7] Getting organization ID..."
ORG_ID=$(curl -s "$BASE/organizations/" -H "$AUTH_HEADER" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
echo "  Org ID: $ORG_ID"

# --- Step 3: Get role IDs ---
echo -e "\n[3/7] Getting role IDs..."
ROLES_JSON=$(curl -s "$BASE/roles/" -H "$AUTH_HEADER")
ARCHITECT_ROLE=$(echo $ROLES_JSON | python3 -c "import sys,json; roles=json.load(sys.stdin); print([r['id'] for r in roles if r['name']=='ARCHITECT'][0])")
ENGINEER_ROLE=$(echo $ROLES_JSON | python3 -c "import sys,json; roles=json.load(sys.stdin); print([r['id'] for r in roles if r['name']=='ENGINEER'][0])")
CLIENT_ROLE=$(echo $ROLES_JSON | python3 -c "import sys,json; roles=json.load(sys.stdin); print([r['id'] for r in roles if r['name']=='CLIENT'][0])")
ADVISORY_ROLE=$(echo $ROLES_JSON | python3 -c "import sys,json; roles=json.load(sys.stdin); print([r['id'] for r in roles if r['name']=='ADOBE_LAUNCH_ADVISORY'][0])")
echo "  ARCHITECT: $ARCHITECT_ROLE"
echo "  ENGINEER:  $ENGINEER_ROLE"
echo "  CLIENT:    $CLIENT_ROLE"
echo "  ADVISORY:  $ADVISORY_ROLE"

# --- Step 4: Create test users ---
echo -e "\n[4/7] Creating test users..."

create_user() {
  local name=$1 email=$2 password=$3
  RESULT=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/users/" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"name\":\"$name\",\"password\":\"$password\",\"organization_id\":\"$ORG_ID\"}")
  if [ "$RESULT" = "201" ]; then
    echo "  Created: $name ($email)"
  elif [ "$RESULT" = "409" ]; then
    echo "  Exists:  $name ($email)"
  else
    echo "  ERROR $RESULT creating $name"
  fi
}

create_user "Sarah Chen" "sarah@apex.dev" "test123"
create_user "Mike Torres" "mike@apex.dev" "test123"
create_user "Lisa Wang" "lisa@client.com" "test123"
create_user "James Park" "james@adobe.com" "test123"

# --- Step 5: Get user IDs ---
echo -e "\n[5/7] Getting user IDs..."
USERS_JSON=$(curl -s "$BASE/users/" -H "$AUTH_HEADER")
SARAH_ID=$(echo $USERS_JSON | python3 -c "import sys,json; users=json.load(sys.stdin); print([u['id'] for u in users if u['email']=='sarah@apex.dev'][0])")
MIKE_ID=$(echo $USERS_JSON | python3 -c "import sys,json; users=json.load(sys.stdin); print([u['id'] for u in users if u['email']=='mike@apex.dev'][0])")
LISA_ID=$(echo $USERS_JSON | python3 -c "import sys,json; users=json.load(sys.stdin); print([u['id'] for u in users if u['email']=='lisa@client.com'][0])")
JAMES_ID=$(echo $USERS_JSON | python3 -c "import sys,json; users=json.load(sys.stdin); print([u['id'] for u in users if u['email']=='james@adobe.com'][0])")
echo "  Sarah:  $SARAH_ID"
echo "  Mike:   $MIKE_ID"
echo "  Lisa:   $LISA_ID"
echo "  James:  $JAMES_ID"

# --- Step 6: Create sample project ---
echo -e "\n[6/7] Creating sample project: 'Acme Corp CJA Migration'..."
PROJECT_JSON=$(curl -s -X POST "$BASE/projects/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "'$ORG_ID'",
    "name": "Acme Corp CJA Migration",
    "client_name": "Acme Corporation",
    "description": "Full AA to CJA migration for Acme Corp — Web, Mobile, and Salesforce data sources"
  }')
PROJECT_ID=$(echo $PROJECT_JSON | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Project ID: $PROJECT_ID"

# --- Step 7: Assign roles on project ---
echo -e "\n[7/7] Assigning project roles..."

assign_role() {
  local user_id=$1 role_id=$2 label=$3
  RESULT=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/projects/$PROJECT_ID/roles" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"$user_id\",\"role_id\":\"$role_id\"}")
  echo "  $label: HTTP $RESULT"
}

assign_role "$SARAH_ID" "$ARCHITECT_ROLE" "Sarah → ARCHITECT"
assign_role "$MIKE_ID" "$ENGINEER_ROLE" "Mike → ENGINEER"
assign_role "$LISA_ID" "$CLIENT_ROLE" "Lisa → CLIENT"
assign_role "$JAMES_ID" "$ADVISORY_ROLE" "James → ADOBE_LAUNCH_ADVISORY"

echo -e "\n========================================="
echo "  SEED COMPLETE"
echo "========================================="
echo ""
echo "Sample Project: Acme Corp CJA Migration"
echo "Project ID:     $PROJECT_ID"
echo ""
echo "Login Credentials:"
echo "  admin@apex.dev    / admin123   (ARCHITECT - creator)"
echo "  sarah@apex.dev    / test123    (ARCHITECT)"
echo "  mike@apex.dev     / test123    (ENGINEER)"
echo "  lisa@client.com   / test123    (CLIENT)"
echo "  james@adobe.com   / test123    (ADOBE_LAUNCH_ADVISORY)"
echo ""
echo "Frontend: http://localhost:3001"
echo "========================================="
```

---

## 4. Module Test Cases

### Legend
- **Persona**: Which user to log in as
- **Expected**: What should happen
- **Verify**: How to confirm the result

---

### M1: Authentication

| # | Test Case | Persona | Steps | Expected |
|---|-----------|---------|-------|----------|
| 1.1 | Valid login | Admin | 1. Go to http://localhost:3001 <br> 2. Enter admin@apex.dev / admin123 <br> 3. Click Login | Redirected to Projects page. Sidebar shows "APEX Admin" and email. |
| 1.2 | Invalid password | — | 1. Enter admin@apex.dev / wrongpass <br> 2. Click Login | Error message "Invalid credentials" shown. Stay on login page. |
| 1.3 | Invalid email | — | 1. Enter nobody@test.com / test123 <br> 2. Click Login | Error message shown. Stay on login page. |
| 1.4 | Logout | Admin | 1. Login as admin <br> 2. Click "Sign out" in sidebar | Redirected to login page. Cannot access /projects directly (redirected to login). |
| 1.5 | Session persistence | Admin | 1. Login as admin <br> 2. Close browser tab <br> 3. Open http://localhost:3001 | Should be auto-logged in (token in localStorage). |
| 1.6 | Login as each persona | All | Login with each of the 5 test users | All users can log in. Name displayed in sidebar matches. |

---

### M2: Projects

| # | Test Case | Persona | Steps | Expected |
|---|-----------|---------|-------|----------|
| 2.1 | View projects list | Admin | 1. Login <br> 2. Click "Projects" in sidebar | Project list shows "Acme Corp CJA Migration" with ACTIVE badge. |
| 2.2 | Create new project | Admin | 1. Click "New Project" <br> 2. Fill: Name="Beta Corp Migration", Client="Beta Corp" <br> 3. Click "Create Project" | New project appears in list. Status is ACTIVE. |
| 2.3 | Navigate to project | Admin | 1. Click on "Acme Corp CJA Migration" | Project detail page loads with header, 9 tabs visible. Dashboard tab active by default. |
| 2.4 | Engineer cannot create | Mike (ENGINEER) | 1. Login as mike@apex.dev <br> 2. Go to Projects page <br> 3. Click "New Project" | Should see the create form but API call fails with 403. |
| 2.5 | Client cannot create | Lisa (CLIENT) | Same as 2.4 | Same — 403 on API call. |

---

### M3: Phases

| # | Test Case | Persona | Steps | Expected |
|---|-----------|---------|-------|----------|
| 3.1 | View phase list | Admin | 1. Open project <br> 2. Click "Phases" tab | 7 phases listed. Phase 1 "Discovery & BRD" is IN_PROGRESS. Phases 2-7 are PENDING. |
| 3.2 | View phase detail | Admin | 1. Click on Phase 1 | Expands to show phase detail with gate criteria. |
| 3.3 | Evaluate gate | Admin | 1. Click "Evaluate Gate" on Phase 1 | Gate evaluation runs. Shows result (likely NOT_MET since no tasks completed). |
| 3.4 | Advance phase (fails) | Admin | 1. Click "Advance Phase" | Should fail — gate criteria not met. Error message shown. |
| 3.5 | Override advance | Admin | 1. Enter override reason: "UAT testing - skip gate" <br> 2. Click override advance | Phase 1 moves to COMPLETED. Phase 2 becomes IN_PROGRESS. |
| 3.6 | Rollback phase | Admin | 1. Click "Rollback" | Phase 2 goes back to PENDING. Phase 1 returns to IN_PROGRESS. |
| 3.7 | Engineer cannot override | Mike (ENGINEER) | 1. Login as Mike <br> 2. Open project → Phases <br> 3. Try to override advance | Should get 403 Forbidden (no override_gate permission). |

---

### M4: Tasks

| # | Test Case | Persona | Steps | Expected |
|---|-----------|---------|-------|----------|
| 4.1 | View task list | Admin | 1. Open project <br> 2. Click "Tasks" tab | Shows 26 tasks across all phases. Status badges visible. |
| 4.2 | Filter by status | Admin | 1. Click "PENDING" filter | Only pending tasks shown. Count updates. |
| 4.3 | View task detail | Admin | 1. Click on any task | Detail panel opens showing: name, classification (AI/HYBRID/MANUAL), owner role, description. |
| 4.4 | Start a task | Admin | 1. Click on "Stakeholder Interview Orchestration" <br> 2. Click "Start" (or update status) | Task status changes to IN_PROGRESS. |
| 4.5 | Complete a task | Admin | 1. On a started task <br> 2. Click "Complete" | Task status changes to COMPLETED. |
| 4.6 | Assign task to user | Admin | 1. Open a task <br> 2. Assign to Mike Torres | Task shows Mike as assigned. |
| 4.7 | Engineer completes own | Mike (ENGINEER) | 1. Login as Mike <br> 2. Find assigned task <br> 3. Complete it | Task marked COMPLETED. Mike has complete_task permission. |
| 4.8 | Client completes own | Lisa (CLIENT) | 1. Login as Lisa <br> 2. Find "Client Production Sign-off" <br> 3. Complete it | Task marked COMPLETED. Signature on gate item. |

---

### M5: Sources

| # | Test Case | Persona | Steps | Expected |
|---|-----------|---------|-------|----------|
| 5.1 | View source definitions | Admin | 1. Open project <br> 2. Click "Sources" tab | Shows 5 source definitions: Web & Mobile, Salesforce, RainFocus, Marketo, 6sense. |
| 5.2 | Select sources | Admin | 1. Check "Web & Mobile (AA)" (mandatory) <br> 2. Check "Salesforce CRM" <br> 3. Click "Select Sources" | Sources selected for project. Source instances created. |
| 5.3 | View source instances | Admin | After 5.2, refresh page | Shows selected sources with layer status (PILOT/DEV/PROD) |
| 5.4 | Verify mandatory source | Admin | Web & Mobile should be pre-checked or required | Mandatory source clearly indicated. |

---

### M6: Documents

| # | Test Case | Persona | Steps | Expected |
|---|-----------|---------|-------|----------|
| 6.1 | View templates | Admin | 1. Open project <br> 2. Click "Documents" tab | Shows 7 templates: BRD, SDR, Implementation Plan, etc. |
| 6.2 | Generate document | Admin | 1. Click "+" next to "BRD (DOCX)" template | New document instance created with DRAFT status. |
| 6.3 | Approve document | Admin | 1. Click checkmark (approve) on the BRD | Document status changes to APPROVED. |
| 6.4 | Reject document | Admin | 1. Generate another document <br> 2. Click X (reject) | Document status changes to REVISION_REQUESTED. |
| 6.5 | Generate multiple | Admin | Generate SDR, Implementation Plan | Multiple documents listed with version numbers. |

---

### M7: Questions

| # | Test Case | Persona | Steps | Expected |
|---|-----------|---------|-------|----------|
| 7.1 | View questions (empty) | Admin | 1. Open project <br> 2. Click "Questions" tab | Shows stats (all 0) and "No questions yet." message. |
| 7.2 | Create question via API | Admin | Use API: POST /questions/ with body: <br> `{"project_id":"<ID>","question_text":"What analytics tools does Acme currently use?","target_role":"CLIENT","question_type":"DISCOVERY"}` | Question appears in list with PENDING status. |
| 7.3 | Answer question | Lisa (CLIENT) | 1. Login as Lisa <br> 2. Open project → Questions <br> 3. Type answer: "We use AA, Google Analytics, and Mixpanel" <br> 4. Press Enter or click Send | Question status changes to ANSWERED. Answer text displayed. |
| 7.4 | Filter questions | Admin | 1. Click "PENDING" filter <br> 2. Click "ANSWERED" filter | Filters work correctly. Count matches. |
| 7.5 | Stats update | Admin | After answering | Stats show Total: 1, Answered: 1, Pending: 0. |
| 7.6 | Create batch via API | Admin | POST /questions/batch with multiple questions | Multiple questions created at once. |

**API commands for creating test questions:**

```bash
# Get token first
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@apex.dev&password=admin123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Replace PROJECT_ID with actual value
PROJECT_ID="<your-project-id>"

# Get the active phase instance ID (required field)
PHASE_ID=$(curl -s "http://localhost:8001/api/v1/phases/project/$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; p=json.load(sys.stdin); print([x['id'] for x in p if x['status']=='IN_PROGRESS'][0])")

# Create individual questions
curl -s -X POST "http://localhost:8001/api/v1/questions/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "phase_instance_id": "'$PHASE_ID'",
    "question_text": "What analytics tools does Acme currently use besides Adobe Analytics?",
    "target_role": "CLIENT",
    "question_type": "DISCOVERY"
  }'

curl -s -X POST "http://localhost:8001/api/v1/questions/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "phase_instance_id": "'$PHASE_ID'",
    "question_text": "How many report suites are active in your AA implementation?",
    "target_role": "CLIENT",
    "question_type": "TECHNICAL"
  }'

curl -s -X POST "http://localhost:8001/api/v1/questions/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "phase_instance_id": "'$PHASE_ID'",
    "question_text": "Are there any custom eVars or events that map to revenue metrics?",
    "target_role": "ENGINEER",
    "question_type": "TECHNICAL"
  }'

curl -s -X POST "http://localhost:8001/api/v1/questions/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "phase_instance_id": "'$PHASE_ID'",
    "question_text": "Does the client use Adobe Launch or DTM for tag management?",
    "target_role": "ADOBE_LAUNCH_ADVISORY",
    "question_type": "TECHNICAL"
  }'

curl -s -X POST "http://localhost:8001/api/v1/questions/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "phase_instance_id": "'$PHASE_ID'",
    "question_text": "What are the top 5 business KPIs tracked in the current AA setup?",
    "target_role": "CLIENT",
    "question_type": "BUSINESS"
  }'
```

---

### M8: Feedback

| # | Test Case | Persona | Steps | Expected |
|---|-----------|---------|-------|----------|
| 8.1 | View feedback (empty) | Admin | 1. Open project <br> 2. Click "Feedback" tab | "No feedback submitted yet." |
| 8.2 | Submit feedback | Admin | 1. Click "Submit Feedback" <br> 2. Select an agent execution (needs one first — see API below) <br> 3. Category: ACCURACY <br> 4. Severity: MEDIUM <br> 5. Score: 0.7 <br> 6. Description: "BRD missing data retention section" <br> 7. Click Submit | Feedback appears in list with severity badge and score. |
| 8.3 | Engineer submits | Mike (ENGINEER) | Same flow as 8.2 | Should succeed — ENGINEER has submit_feedback. |
| 8.4 | Client cannot submit | Lisa (CLIENT) | 1. Login as Lisa <br> 2. Try to submit feedback | Should get 403 — CLIENT lacks submit_feedback. |
| 8.5 | Advisory submits | James (ADVISORY) | Same as 8.2 | Should succeed — ADOBE_LAUNCH_ADVISORY has submit_feedback. |

**Create an agent execution first (needed for feedback):**

```bash
# Get an agent definition ID
AGENT_DEF_ID=$(curl -s "http://localhost:8001/api/v1/agents/definitions" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

# Get a task instance ID
TASK_ID=$(curl -s "http://localhost:8001/api/v1/tasks/?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

# Create execution
curl -s -X POST "http://localhost:8001/api/v1/agents/executions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_definition_id": "'$AGENT_DEF_ID'",
    "project_id": "'$PROJECT_ID'",
    "task_instance_id": "'$TASK_ID'",
    "input_data": {"prompt": "Generate stakeholder interview questions"}
  }'
```

---

### M9: Costs & Tracking

| # | Test Case | Persona | Steps | Expected |
|---|-----------|---------|-------|----------|
| 9.1 | View costs (empty) | Admin | 1. Open project <br> 2. Click "Costs" tab | Shows $0.00 total cost, 0 tokens, 0 entries. |
| 9.2 | Costs after execution | Admin | After creating agent execution with cost data | Cost cards update with totals. |
| 9.3 | Engineer cannot view | Mike (ENGINEER) | 1. Login as Mike <br> 2. Open project → Costs tab | Error: "Unable to load cost data (requires ARCHITECT role)." |
| 9.4 | Client cannot view | Lisa (CLIENT) | Same as 9.3 | Same error message. |

---

### M10: Audit Log

| # | Test Case | Persona | Steps | Expected |
|---|-----------|---------|-------|----------|
| 10.1 | View audit log | Admin | 1. Open project <br> 2. Click "Audit" tab | Shows audit entries (at least project creation). Columns: Action, Entity, Actor, Time. |
| 10.2 | Summary shows counts | Admin | After various actions | Summary section shows action type counts (e.g., "CREATE_PROJECT: 1"). |
| 10.3 | Engineer cannot view | Mike (ENGINEER) | 1. Login as Mike <br> 2. Open project → Audit tab | Error: "Unable to load audit log (requires ARCHITECT role)." |

---

### M11: Notifications

| # | Test Case | Persona | Steps | Expected |
|---|-----------|---------|-------|----------|
| 11.1 | View notifications | Admin | Click "Notifications" in sidebar | Shows notification list (may be empty initially). |
| 11.2 | Create notification via API | — | See API command below | Notification appears with type, severity, and message. |
| 11.3 | Unread badge | Admin | After creating notification | Red badge on "Notifications" in sidebar shows count. |
| 11.4 | Mark as read | Admin | 1. Click "Mark read" on a notification | Notification visual changes (no longer highlighted). Badge count decreases. |
| 11.5 | Mark all read | Admin | 1. Click "Mark all read" | All notifications marked read. Badge disappears. |

**Create test notifications:**

```bash
ADMIN_USER_ID="<paste-admin-user-id>"

curl -s -X POST "http://localhost:8001/api/v1/notifications/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$ADMIN_USER_ID'",
    "project_id": "'$PROJECT_ID'",
    "type": "PHASE_GATE",
    "title": "Gate Evaluation Result",
    "body": "Phase 1 gate evaluation completed — criteria NOT MET"
  }'

curl -s -X POST "http://localhost:8001/api/v1/notifications/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$ADMIN_USER_ID'",
    "project_id": "'$PROJECT_ID'",
    "type": "TASK",
    "title": "Task Completed",
    "body": "Task Stakeholder Interview Orchestration completed by Mike Torres"
  }'

curl -s -X POST "http://localhost:8001/api/v1/notifications/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$ADMIN_USER_ID'",
    "project_id": "'$PROJECT_ID'",
    "type": "QUESTION",
    "title": "Questions Answered",
    "body": "Lisa Wang answered 3 pending questions"
  }'
```

---

### M12: Improvements

| # | Test Case | Persona | Steps | Expected |
|---|-----------|---------|-------|----------|
| 12.1 | View improvements | Admin | Click "Improvements" in sidebar | Shows improvement proposals (may have 1 from earlier testing). |
| 12.2 | Filter by project | Admin | Select project from dropdown | Only that project's improvements shown. |
| 12.3 | Approve improvement | Admin | Click checkmark on a PROPOSED improvement | Status changes to APPROVED. |
| 12.4 | Reject improvement | Admin | Click X on a PROPOSED improvement | Status changes to REJECTED. |
| 12.5 | Engineer cannot review | Mike (ENGINEER) | Try to approve/reject | API returns 403 — no review_improvements permission. |

**Create test improvement:**

```bash
curl -s -X POST "http://localhost:8001/api/v1/improvements/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "title": "Improve BRD generation prompt",
    "description": "Add data retention and compliance sections to BRD template based on client feedback",
    "category": "PROMPT_IMPROVEMENT",
    "priority": "HIGH",
    "source_type": "FEEDBACK",
    "expected_impact": "Reduce BRD revision requests by 40%"
  }'

curl -s -X POST "http://localhost:8001/api/v1/improvements/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "'$PROJECT_ID'",
    "title": "Add schema naming convention validation",
    "description": "Schema agent should validate field names follow XDM naming conventions before submission",
    "category": "PROCESS_IMPROVEMENT",
    "priority": "MEDIUM",
    "source_type": "EVAL_RESULT",
    "expected_impact": "Reduce schema validation failures by 60%"
  }'
```

---

### M13: RBAC & Permissions

This section tests that each persona can ONLY do what their role allows.

#### As ARCHITECT (sarah@apex.dev)

| # | Action | Expected |
|---|--------|----------|
| 13.1 | View all projects | YES — sees all projects |
| 13.2 | Create project | YES |
| 13.3 | Assign roles | YES |
| 13.4 | Override gate | YES |
| 13.5 | View audit log | YES — data loads |
| 13.6 | View costs | YES — data loads |
| 13.7 | Submit feedback | YES |
| 13.8 | Review improvements | YES — approve/reject buttons visible |
| 13.9 | Answer questions | YES |

#### As ENGINEER (mike@apex.dev)

| # | Action | Expected |
|---|--------|----------|
| 13.10 | View all projects | NO — only assigned projects |
| 13.11 | Create project | NO — 403 on API call |
| 13.12 | Assign roles | NO — 403 |
| 13.13 | Override gate | NO — 403 |
| 13.14 | View audit log | NO — error message shown |
| 13.15 | View costs | NO — error message shown |
| 13.16 | Submit feedback | YES |
| 13.17 | Review improvements | NO — 403 |
| 13.18 | Complete own tasks | YES |
| 13.19 | Answer questions | YES |

#### As CLIENT (lisa@client.com)

| # | Action | Expected |
|---|--------|----------|
| 13.20 | View all projects | NO — only assigned projects |
| 13.21 | Create project | NO — 403 |
| 13.22 | Complete own tasks | YES (sign-offs) |
| 13.23 | Sign-off gate | YES |
| 13.24 | Submit feedback | NO — 403 |
| 13.25 | View audit | NO — error |
| 13.26 | View costs | NO — error |
| 13.27 | Answer questions | YES |

#### As ADOBE_LAUNCH_ADVISORY (james@adobe.com)

| # | Action | Expected |
|---|--------|----------|
| 13.28 | View all projects | NO — only assigned projects |
| 13.29 | Complete own tasks | YES |
| 13.30 | Submit feedback | YES |
| 13.31 | Answer questions | YES |
| 13.32 | Override gate | NO — 403 |
| 13.33 | Review improvements | NO — 403 |
| 13.34 | View audit | NO — error |
| 13.35 | View costs | NO — error |

---

## 5. End-to-End Scenario

Full migration lifecycle for "Acme Corp CJA Migration":

### Act 1: Project Setup (Admin / ARCHITECT)

```
Login: admin@apex.dev / admin123
```

1. Go to Projects → verify "Acme Corp CJA Migration" exists
2. Click into the project
3. **Dashboard tab**: Verify summary cards (26 tasks, 0 completed)
4. **Sources tab**: Select "Web & Mobile (AA)" + "Salesforce CRM"
5. **Phases tab**: Verify Phase 1 is IN_PROGRESS

### Act 2: Discovery Phase (Multi-persona)

**As Admin (ARCHITECT):**
6. **Tasks tab**: Start "Stakeholder Interview Orchestration"
7. **Tasks tab**: Start "Current-State Analytics Audit"
8. Create questions via API (use commands from M7 above)

**As Lisa (CLIENT):**
9. Login as lisa@client.com / test123
10. **Questions tab**: Answer the CLIENT-targeted questions
11. Verify stats update

**As James (ADVISORY):**
12. Login as james@adobe.com / test123
13. **Questions tab**: Answer the ADOBE_LAUNCH_ADVISORY question
14. Verify answered questions show green

**As Admin (ARCHITECT):**
15. **Tasks tab**: Complete "Stakeholder Interview Orchestration"
16. **Tasks tab**: Complete "Current-State Analytics Audit"
17. **Documents tab**: Generate BRD from template
18. Approve the BRD document
19. **Tasks tab**: Complete "BRD Generation"
20. Complete remaining Phase 1 tasks

### Act 3: Phase Transition

**As Admin (ARCHITECT):**
21. **Phases tab**: Click "Evaluate Gate" on Phase 1
22. If criteria not met → use "Override Advance" with reason: "All discovery tasks completed, BRD approved"
23. Verify Phase 1 → COMPLETED, Phase 2 → IN_PROGRESS

**As Mike (ENGINEER):**
24. Login as mike@apex.dev / test123
25. Verify Phase 2 tasks are now visible
26. **Phases tab**: Try to override advance → should get 403

### Act 4: Feedback & Improvements

**As Mike (ENGINEER):**
27. **Feedback tab**: Submit feedback on BRD quality
    - Category: COMPLETENESS, Severity: MEDIUM
    - Score: 0.8
    - Description: "BRD covers most requirements but missing data retention policies"

**As Admin (ARCHITECT):**
28. **Feedback tab**: Verify Mike's feedback is visible
29. **Improvements** (sidebar): Review improvement proposals
30. Approve the BRD improvement proposal

### Act 5: Monitoring & Verification

**As Admin (ARCHITECT):**
31. **Costs tab**: Verify cost tracking cards
32. **Audit tab**: Verify all actions logged (project creation, task updates, phase advances)
33. **Notifications** (sidebar): Check for any notifications, mark as read
34. **Dashboard tab**: Verify updated stats (completed tasks, phase progress)

### Act 6: RBAC Verification

35. Login as each persona and verify restricted tabs show error messages:
    - Mike (ENGINEER): Costs → error, Audit → error
    - Lisa (CLIENT): Costs → error, Audit → error, Feedback → can't submit
    - James (ADVISORY): Costs → error, Audit → error

---

## 6. Quick Reference — API Cheat Sheet

All examples use `$TOKEN` and `$PROJECT_ID` variables. Set them first:

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@apex.dev&password=admin123" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

PROJECT_ID="<paste-your-project-id>"
H="Authorization: Bearer $TOKEN"
```

| Action | Command |
|--------|---------|
| **List projects** | `curl -s http://localhost:8001/api/v1/projects/ -H "$H"` |
| **Get project detail** | `curl -s http://localhost:8001/api/v1/projects/$PROJECT_ID -H "$H"` |
| **List phases** | `curl -s http://localhost:8001/api/v1/phases/project/$PROJECT_ID -H "$H"` |
| **Evaluate gate** | `curl -s -X POST http://localhost:8001/api/v1/phases/<PHASE_ID>/evaluate-gate -H "$H"` |
| **Advance phase** | `curl -s -X POST http://localhost:8001/api/v1/phases/project/$PROJECT_ID/advance -H "$H"` |
| **Override advance** | `curl -s -X POST http://localhost:8001/api/v1/phases/project/$PROJECT_ID/advance-override -H "$H" -H "Content-Type: application/json" -d '{"reason":"UAT test"}'` |
| **List tasks** | `curl -s "http://localhost:8001/api/v1/tasks/?project_id=$PROJECT_ID" -H "$H"` |
| **Complete task** | `curl -s -X POST http://localhost:8001/api/v1/tasks/<TASK_ID>/complete -H "$H" -H "Content-Type: application/json" -d '{}'` |
| **List questions** | `curl -s "http://localhost:8001/api/v1/questions/?project_id=$PROJECT_ID" -H "$H"` |
| **Answer question** | `curl -s -X POST http://localhost:8001/api/v1/questions/<Q_ID>/answer -H "$H" -H "Content-Type: application/json" -d '{"answer":"The answer"}'` |
| **Get costs** | `curl -s http://localhost:8001/api/v1/costs/project/$PROJECT_ID -H "$H"` |
| **List notifications** | `curl -s http://localhost:8001/api/v1/notifications/ -H "$H"` |
| **List improvements** | `curl -s http://localhost:8001/api/v1/improvements/ -H "$H"` |
| **Audit log** | `curl -s "http://localhost:8001/api/v1/audit/?project_id=$PROJECT_ID&limit=50" -H "$H"` |

---

## Defect Reporting Template

When you find an issue, log it with:

```
DEFECT #___
Module: M<number> - <module name>
Test Case: <test case #>
Persona: <which user>
Steps to Reproduce: <exact steps>
Expected: <what should happen>
Actual: <what actually happened>
Severity: BLOCKER / MAJOR / MINOR / COSMETIC
Screenshot: <attach if applicable>
```
