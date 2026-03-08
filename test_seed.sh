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
ADMIN_ID=$(echo $USERS_JSON | python3 -c "import sys,json; users=json.load(sys.stdin); print([u['id'] for u in users if u['email']=='admin@apex.dev'][0])")
SARAH_ID=$(echo $USERS_JSON | python3 -c "import sys,json; users=json.load(sys.stdin); print([u['id'] for u in users if u['email']=='sarah@apex.dev'][0])")
MIKE_ID=$(echo $USERS_JSON | python3 -c "import sys,json; users=json.load(sys.stdin); print([u['id'] for u in users if u['email']=='mike@apex.dev'][0])")
LISA_ID=$(echo $USERS_JSON | python3 -c "import sys,json; users=json.load(sys.stdin); print([u['id'] for u in users if u['email']=='lisa@client.com'][0])")
JAMES_ID=$(echo $USERS_JSON | python3 -c "import sys,json; users=json.load(sys.stdin); print([u['id'] for u in users if u['email']=='james@adobe.com'][0])")
echo "  Admin:  $ADMIN_ID"
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

# --- Step 8: Seed sample data ---
echo -e "\n[BONUS] Creating sample test data..."

# Select sources
echo "  Selecting sources..."
SOURCE_DEFS=$(curl -s "$BASE/sources/definitions" -H "$AUTH_HEADER")
WEB_SOURCE_ID=$(echo $SOURCE_DEFS | python3 -c "import sys,json; defs=json.load(sys.stdin); print([d['id'] for d in defs if d['source_type']=='WEB_MOBILE'][0])")
SF_SOURCE_ID=$(echo $SOURCE_DEFS | python3 -c "import sys,json; defs=json.load(sys.stdin); print([d['id'] for d in defs if d['source_type']=='SALESFORCE'][0])")
curl -s -o /dev/null -w "  Sources selected: HTTP %{http_code}\n" -X POST "$BASE/sources/project/$PROJECT_ID/select" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d "{\"source_definition_ids\":[\"$WEB_SOURCE_ID\",\"$SF_SOURCE_ID\"]}"

# Get phase instance ID (needed for questions)
PHASE_ID=$(curl -s "$BASE/phases/project/$PROJECT_ID" -H "$AUTH_HEADER" | python3 -c "import sys,json; p=json.load(sys.stdin); print([x['id'] for x in p if x['status']=='IN_PROGRESS'][0])")

# Create questions
echo "  Creating sample questions..."
for Q in \
  '{"project_id":"'$PROJECT_ID'","phase_instance_id":"'$PHASE_ID'","question_text":"What analytics tools does Acme currently use besides Adobe Analytics?","target_role":"CLIENT","question_type":"DISCOVERY"}' \
  '{"project_id":"'$PROJECT_ID'","phase_instance_id":"'$PHASE_ID'","question_text":"How many report suites are active in your AA implementation?","target_role":"CLIENT","question_type":"TECHNICAL"}' \
  '{"project_id":"'$PROJECT_ID'","phase_instance_id":"'$PHASE_ID'","question_text":"Are there any custom eVars or events that map to revenue metrics?","target_role":"ENGINEER","question_type":"TECHNICAL"}' \
  '{"project_id":"'$PROJECT_ID'","phase_instance_id":"'$PHASE_ID'","question_text":"Does the client use Adobe Launch or DTM for tag management?","target_role":"ADOBE_LAUNCH_ADVISORY","question_type":"TECHNICAL"}' \
  '{"project_id":"'$PROJECT_ID'","phase_instance_id":"'$PHASE_ID'","question_text":"What are the top 5 business KPIs tracked in the current AA setup?","target_role":"CLIENT","question_type":"BUSINESS"}'
do
  curl -s -o /dev/null -X POST "$BASE/questions/" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "$Q"
done
echo "  5 questions created."

# Create notifications
echo "  Creating sample notifications..."
curl -s -o /dev/null -X POST "$BASE/notifications/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"'$ADMIN_ID'","project_id":"'$PROJECT_ID'","type":"PHASE_GATE","title":"Gate Evaluation Pending","body":"Phase 1 Discovery gate evaluation pending — 5 tasks remaining","action_url":"/projects/'$PROJECT_ID'/phases"}'
curl -s -o /dev/null -X POST "$BASE/notifications/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"'$ADMIN_ID'","project_id":"'$PROJECT_ID'","type":"QUESTION","title":"Questions Awaiting Response","body":"3 new questions awaiting client response for Acme Corp project","action_url":"/projects/'$PROJECT_ID'/questions"}'
curl -s -o /dev/null -X POST "$BASE/notifications/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"'$ADMIN_ID'","project_id":"'$PROJECT_ID'","type":"TASK","title":"Task Assigned","body":"You have been assigned Stakeholder Interview Orchestration","action_url":"/projects/'$PROJECT_ID'/tasks"}'
echo "  3 notifications created."

# Create improvements
echo "  Creating sample improvements..."
curl -s -o /dev/null -X POST "$BASE/improvements/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"'$PROJECT_ID'","title":"Improve BRD generation prompt","description":"Add data retention and compliance sections to BRD template based on client feedback","category":"PROMPT_IMPROVEMENT","priority":"HIGH","source_type":"FEEDBACK","expected_impact":"Reduce BRD revision requests by 40%"}'
curl -s -o /dev/null -X POST "$BASE/improvements/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"'$PROJECT_ID'","title":"Add schema naming convention validation","description":"Schema agent should validate field names follow XDM naming conventions before submission","category":"PROCESS_IMPROVEMENT","priority":"MEDIUM","source_type":"EVAL_RESULT","expected_impact":"Reduce schema validation failures by 60%"}'
echo "  2 improvements created."

# Create an agent execution (needed for feedback testing)
echo "  Creating sample agent execution..."
AGENT_DEF_ID=$(curl -s "$BASE/agents/definitions" -H "$AUTH_HEADER" | python3 -c "import sys,json; defs=json.load(sys.stdin); print([d['id'] for d in defs if d['name']=='discovery'][0])")
TASK_ID=$(curl -s "$BASE/tasks/?project_id=$PROJECT_ID" -H "$AUTH_HEADER" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
EXEC_JSON=$(curl -s -X POST "$BASE/agents/executions" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"agent_definition_id":"'$AGENT_DEF_ID'","project_id":"'$PROJECT_ID'","task_instance_id":"'$TASK_ID'","triggered_by":"admin@apex.dev","input_context":{"prompt":"Generate stakeholder interview questions for Acme Corp AA to CJA migration"}}')
EXEC_ID=$(echo $EXEC_JSON | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','FAILED'))" 2>/dev/null || echo "FAILED")
echo "  Agent execution: $EXEC_ID"

# Generate a document
echo "  Generating sample BRD document..."
BRD_TEMPLATE_ID=$(curl -s "$BASE/documents/templates" -H "$AUTH_HEADER" | python3 -c "import sys,json; t=json.load(sys.stdin); print([x['id'] for x in t if x['name']=='BRD'][0])")
PHASE_ID=$(curl -s "$BASE/phases/project/$PROJECT_ID" -H "$AUTH_HEADER" | python3 -c "import sys,json; p=json.load(sys.stdin); print([x['id'] for x in p if x['status']=='IN_PROGRESS'][0])")
curl -s -o /dev/null -X POST "$BASE/documents/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"document_template_id":"'$BRD_TEMPLATE_ID'","project_id":"'$PROJECT_ID'","phase_instance_id":"'$PHASE_ID'"}'
echo "  BRD document generated."

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
echo "Pre-loaded Data:"
echo "  - 2 sources selected (Web & Mobile + Salesforce)"
echo "  - 5 questions (3 for CLIENT, 1 ENGINEER, 1 ADVISORY)"
echo "  - 3 notifications"
echo "  - 2 improvement proposals"
echo "  - 1 agent execution (Discovery)"
echo "  - 1 BRD document (DRAFT)"
echo ""
echo "Frontend: http://localhost:3001"
echo "========================================="
