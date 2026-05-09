from flask import Flask, render_template, request, flash, redirect, url_for, session
import csv
import io
import os
import json
import uuid
import datetime
import base64

app = Flask(__name__)
app.secret_key = 'super_secret_royal_key_for_the_crown_dashboard'

DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
MASTER_JSON = os.path.join(DATA_FOLDER, 'master_data.json')
ADMINS_JSON = os.path.join(DATA_FOLDER, 'admins.json')
MOTIONS_JSON = os.path.join(DATA_FOLDER, 'motions.json')
TIMER_JSON = os.path.join(DATA_FOLDER, 'timer.json')
AUDIT_JSON = os.path.join(DATA_FOLDER, 'audit_log.json')
ARCHIVE_INDEX_JSON = os.path.join(DATA_FOLDER, 'archives_index.json')
ARCHIVE_DIR = os.path.join(DATA_FOLDER, 'archives')
TOURNAMENTS_INDEX_JSON = os.path.join(DATA_FOLDER, 'tournaments_index.json')
TOURNAMENTS_DIR = os.path.join(DATA_FOLDER, 'tournaments')

os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)
os.makedirs(TOURNAMENTS_DIR, exist_ok=True)

def load_audit():
    if os.path.exists(AUDIT_JSON):
        with open(AUDIT_JSON, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return []
    return []

def save_audit(audit_data):
    with open(AUDIT_JSON, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, indent=4)

def log_action(category, details):
    admin_name = session.get('admin_user', 'System')
    audit_data = load_audit()
    audit_data.insert(0, {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "admin_name": admin_name,
        "category": category,
        "details": details
    })
    save_audit(audit_data)


def load_archives_index():
    if os.path.exists(ARCHIVE_INDEX_JSON):
        with open(ARCHIVE_INDEX_JSON, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return []
    return []

def save_archives_index(data):
    with open(ARCHIVE_INDEX_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def load_admins():
    if os.path.exists(ADMINS_JSON):
        with open(ADMINS_JSON, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_admins(admins):
    with open(ADMINS_JSON, 'w', encoding='utf-8') as f:
        json.dump(admins, f, indent=4)

def load_motions():
    if os.path.exists(MOTIONS_JSON):
        with open(MOTIONS_JSON, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_motions(motions):
    with open(MOTIONS_JSON, 'w', encoding='utf-8') as f:
        json.dump(motions, f, indent=4)

def load_timer_presets():
    if os.path.exists(TIMER_JSON):
        with open(TIMER_JSON, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass
    return []

def save_timer_presets(presets):
    with open(TIMER_JSON, 'w', encoding='utf-8') as f:
        json.dump(presets, f, indent=4)

# --- TOURNAMENT WORKSPACE SYSTEM ---

def load_tournaments_index():
    if os.path.exists(TOURNAMENTS_INDEX_JSON):
        with open(TOURNAMENTS_INDEX_JSON, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"active_id": None, "tournaments": []}
    return {"active_id": None, "tournaments": []}

def save_tournaments_index(data):
    with open(TOURNAMENTS_INDEX_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def get_active_tournament_path():
    index = load_tournaments_index()
    active_id = index.get("active_id")
    if active_id:
        path = os.path.join(TOURNAMENTS_DIR, f"{active_id}.json")
        if os.path.exists(path):
            return path
    return MASTER_JSON

def migrate_to_tournament_system():
    """On first run, migrate legacy master_data.json into the tournament workspace system."""
    if os.path.exists(TOURNAMENTS_INDEX_JSON):
        return
    tournament_id = str(uuid.uuid4())[:8]
    dest = os.path.join(TOURNAMENTS_DIR, f"{tournament_id}.json")
    if os.path.exists(MASTER_JSON):
        import shutil
        shutil.copy(MASTER_JSON, dest)
    else:
        with open(dest, 'w', encoding='utf-8') as f:
            json.dump({"Candidates": {}, "Rounds": {}, "OutroundTeams": {}}, f, indent=4)
    index = {
        "active_id": tournament_id,
        "tournaments": [{
            "id": tournament_id,
            "name": "Default Tournament",
            "created": datetime.datetime.now().strftime("%Y-%m-%d"),
            "status": "active"
        }]
    }
    save_tournaments_index(index)

migrate_to_tournament_system()

def load_data():
    path = get_active_tournament_path()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if "Candidates" not in data:
                    data = {"Candidates": data, "Rounds": {}}
                if "OutroundTeams" not in data:
                    data["OutroundTeams"] = {}
                return data
            except json.JSONDecodeError:
                return {"Candidates": {}, "Rounds": {}, "OutroundTeams": {}}
    return {"Candidates": {}, "Rounds": {}, "OutroundTeams": {}}

def save_data(data):
    path = get_active_tournament_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def get_sorted_candidates(master_data):
    raw_data = master_data.get("Candidates", {})
    processed_data = []
    
    for candidate_name, info in raw_data.items():
        if candidate_name.startswith("SWING_"): 
            continue
            
        total = 0.0
        prelims = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6']
        for r in prelims:
            val = info.get(r, 0)
            if val:
                total += float(val)
                
        wins = int(info.get('Wins', 0))
                
        info['Total Marks_calculated'] = round(total, 2)
        info['Total Marks'] = f"{total:.2f}"
        info['WinsNum'] = wins
        
        processed_data.append(info)
        
    group_a = [x for x in processed_data if x['WinsNum'] >= 4]
    group_b = [x for x in processed_data if x['WinsNum'] < 4]
    
    group_a.sort(key=lambda x: x['Total Marks_calculated'], reverse=True)
    group_b.sort(key=lambda x: x['Total Marks_calculated'], reverse=True)
    
    return group_a + group_b

@app.route('/', methods=['GET'])
def index():
    master = load_data()
    final_sorted_data = get_sorted_candidates(master)
    is_admin = session.get('is_admin', False)
    is_master = session.get('is_master', False)
    outround_teams = master.get("OutroundTeams", {})
    return render_template('index.html', data=final_sorted_data, candidates=master.get("Candidates", {}), is_admin=is_admin, is_master=is_master, outround_teams=outround_teams)

@app.route('/matches')
def matches():
    master = load_data()
    all_rounds = master.get("Rounds", {})
    is_admin = session.get('is_admin', False)
    is_master = session.get('is_master', False)
    teams = master.get("OutroundTeams", {})
    
    prelim_rounds = {k: v for k, v in all_rounds.items() if k in ['R1', 'R2', 'R3', 'R4', 'R5', 'R6']}
    outround_matches = {k: v for k, v in all_rounds.items() if k in ['Octofinals', 'Quarterfinals', 'Semifinals', 'Finals']}
    
    # Mathematical Cascading Logic for Matchmaker
    def get_winners(r_name):
        return [m['winner_leader'] for m in all_rounds.get(r_name, []) if m.get('status') == 'Completed' and m.get('winner_leader')]
        
    octo_winners = get_winners('Octofinals')
    quarter_winners = get_winners('Quarterfinals')
    semi_winners = get_winners('Semifinals')
    
    if len(octo_winners) < 8:
        active_outround = 'Octofinals'
        eligible_pool = list(teams.keys())
    elif len(quarter_winners) < 4:
        active_outround = 'Quarterfinals'
        eligible_pool = octo_winners
    elif len(semi_winners) < 2:
        active_outround = 'Semifinals'
        eligible_pool = quarter_winners
    else:
        active_outround = 'Finals'
        eligible_pool = semi_winners
        
    # Filter out those already scheduled in the active round
    already_scheduled = []
    for m in all_rounds.get(active_outround, []):
        already_scheduled.extend([m.get('team1_leader'), m.get('team2_leader')])
        
    eligible_match_leaders = [leader for leader in eligible_pool if leader not in already_scheduled]
    
    all_motions = load_motions()
    published_motions = [m for m in all_motions if m['published']]

    return render_template('matches.html', rounds=prelim_rounds, outround_matches=outround_matches, teams=teams, is_admin=is_admin, is_master=is_master, active_outround=active_outround, eligible_match_leaders=eligible_match_leaders, candidates=master.get('Candidates', {}), motions=published_motions)

@app.route('/admin/registration')
def admin_registration():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    master = load_data()
    is_master = session.get('is_master', False)
    
    return render_template('admin_registration.html', 
                            candidates=master.get('Candidates', {}), 
                            is_admin=True, 
                            is_master=is_master)

@app.route('/admin/register', methods=['POST'])
def register_candidate():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    name = request.form.get('candidate_name', '').strip()
    alias = request.form.get('alias', '').strip()
    debate_class = request.form.get('debate_class', '').strip()
    debate_level = request.form.get('debate_level', '').strip()
    institute = request.form.get('institute', '').strip()
    phone = request.form.get('phone', '').strip()
    notes = request.form.get('notes', '').strip()
    
    cropped_b64 = request.form.get('cropped_avatar', '').strip()
    avatar_file = request.files.get('avatar')
    avatar_filename = None
    
    safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
    safe_name = safe_name.replace(' ', '_').lower()
    
    if cropped_b64 and ',' in cropped_b64:
        img_data = cropped_b64.split(',')[1]
        img_bytes = base64.b64decode(img_data)
        filename = f"{safe_name}_{str(uuid.uuid4())[:6]}.png"
        target_dir = os.path.join(app.root_path, 'static', 'avatars')
        os.makedirs(target_dir, exist_ok=True)
        filepath = os.path.join(target_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(img_bytes)
        avatar_filename = filename
    elif avatar_file and avatar_file.filename != '':
        ext = avatar_file.filename.rsplit('.', 1)[-1].lower() if '.' in avatar_file.filename else 'png'
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            ext = 'png'
        filename = f"{safe_name}_{str(uuid.uuid4())[:6]}.{ext}"
        target_dir = os.path.join(app.root_path, 'static', 'avatars')
        os.makedirs(target_dir, exist_ok=True)
        filepath = os.path.join(target_dir, filename)
        avatar_file.save(filepath)
        avatar_filename = filename
    
    if not name:
        flash('Candidate name is required.')
        return redirect(url_for('admin_registration'))
        
    master = load_data()
    if name not in master['Candidates']:
        master['Candidates'][name] = {
            'Candidate Name': name,
            'Alias': alias if alias else None,
            'Class': debate_class,
            'Level': debate_level,
            'Institute': institute,
            'Phone': phone,
            'Notes': notes,
            'Wins': 0
        }
        if avatar_filename:
            master['Candidates'][name]['Avatar'] = avatar_filename
        save_data(master)
        log_action('CANDIDATE_REGISTERED', f'Registered new candidate: {name}')
        flash(f'Candidate {name} successfully registered.')
    else:
        flash(f'Candidate {name} already exists!')
        
    return redirect(url_for('admin_registration'))

@app.route('/admin/create_outround_team', methods=['POST'])
def create_outround_team():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    leader = request.form.get('leader')
    if not leader:
        flash("A leader must be nominated to form an Outround Team.")
        return redirect(url_for('matches_outrounds'))

        
    supporters = []
    for i in range(1, 6):
        sup = request.form.get(f'supporter_{i}', '').strip()
        if sup:
            supporters.append(sup)
            
    master = load_data()
    
    if leader in master['OutroundTeams']:
        flash(f"{leader} is already leading a permanent team.")
        return redirect(url_for('matches_outrounds'))

        
    master['OutroundTeams'][leader] = {
        "Leader": leader,
        "Supporters": supporters
    }
    
    save_data(master)
    flash(f"Permanent team formed under {leader}!")
    return redirect(url_for('matches_outrounds'))

@app.route('/admin/disband_outround_team', methods=['POST'])
def disband_outround_team():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    leader = request.form.get('leader')
    master = load_data()
    
    # Ghost Reference Bug Fix: Prevent disbanding if they are actively scheduled
    for r_name in ['Octofinals', 'Quarterfinals', 'Semifinals', 'Finals']:
        for m in master.get('Rounds', {}).get(r_name, []):
            if m.get('team1_leader') == leader or m.get('team2_leader') == leader:
                flash(f"Error: Team under {leader} is actively scheduled in {r_name}. You must reset their match before disbanding the team.")
                return redirect(url_for('matches_outrounds'))
    
    if leader in master['OutroundTeams']:
        del master['OutroundTeams'][leader]
        save_data(master)
        flash(f"Team {leader} has been mathematically disbanded. Members returned to pools.")
        
    return redirect(url_for('matches_outrounds'))

@app.route('/matches/outrounds')
def matches_outrounds():        
    master = load_data()
    all_rounds = master.get("Rounds", {})
    is_admin = session.get('is_admin', False)
    is_master = session.get('is_master', False)
    teams = master.get("OutroundTeams", {})
    
    all_sorted = get_sorted_candidates(master)
    top_16 = [c['Candidate Name'] for c in all_sorted[:16]]
    eliminated = [c['Candidate Name'] for c in all_sorted[16:]]
    
    used_leaders = list(teams.keys())
    used_supporters = []
    for leader, data in teams.items():
        used_supporters.extend(data.get('Supporters', []))
        
    available_leaders = [c for c in top_16 if c not in used_leaders]
    available_supporters = [c for c in eliminated if c not in used_supporters]
    
    outround_matches = {k: v for k, v in all_rounds.items() if k in ['Octofinals', 'Quarterfinals', 'Semifinals', 'Finals']}
    
    def get_winners(r_name):
        return [m['winner_leader'] for m in all_rounds.get(r_name, []) if m.get('status') == 'Completed' and m.get('winner_leader')]
        
    octo_winners = get_winners('Octofinals')
    quarter_winners = get_winners('Quarterfinals')
    semi_winners = get_winners('Semifinals')
    
    if len(octo_winners) < 8:
        active_outround = 'Octofinals'
        eligible_pool = list(teams.keys())
    elif len(quarter_winners) < 4:
        active_outround = 'Quarterfinals'
        eligible_pool = octo_winners
    elif len(semi_winners) < 2:
        active_outround = 'Semifinals'
        eligible_pool = quarter_winners
    else:
        active_outround = 'Finals'
        eligible_pool = semi_winners
        
    already_scheduled = []
    for m in all_rounds.get(active_outround, []):
        already_scheduled.extend([m.get('team1_leader'), m.get('team2_leader')])
        
    eligible_match_leaders = [leader for leader in eligible_pool if leader not in already_scheduled]
    
    return render_template('outrounds.html', 
                           teams=teams, 
                           available_leaders=available_leaders, 
                           available_supporters=available_supporters,
                            is_admin=is_admin,
                           is_master=is_master,
                           outround_matches=outround_matches,
                           active_outround=active_outround,
                           eligible_match_leaders=eligible_match_leaders)

@app.route('/match_poster/<match_id>')
def match_poster(match_id):
    master = load_data()
    candidates = master.get("Candidates", {})
    target_match = None
    target_round = None
    
    for r_name, m_list in master.get("Rounds", {}).items():
        for m in m_list:
            if m["id"] == match_id:
                target_match = m
                target_round = r_name
                break
                
    if not target_match:
        flash("Match not found.")
        return redirect(request.referrer or url_for('matches'))
        
    t1_players = []
    t2_players = []
    
    if target_match.get('is_outround'):
        l1 = target_match.get('team1_leader')
        if l1 in candidates:
            c = candidates[l1].copy()
            c['Name'] = l1
            t1_players.append(c)
        l2 = target_match.get('team2_leader')
        if l2 in candidates:
            c = candidates[l2].copy()
            c['Name'] = l2
            t2_players.append(c)
    else:
        for p in target_match.get('team1', []):
            if not p.startswith("SWING_") and p in candidates:
                c = candidates[p].copy()
                c['Name'] = p
                t1_players.append(c)
        for p in target_match.get('team2', []):
            if not p.startswith("SWING_") and p in candidates:
                c = candidates[p].copy()
                c['Name'] = p
                t2_players.append(c)

    return render_template('match_poster.html', match=target_match, round_name=target_round, t1_players=t1_players, t2_players=t2_players)

@app.route('/admin/create_match', methods=['POST'])
def create_match():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    round_name = request.form.get('round_name')
    team1 = [request.form.get(f't1_m{i}', '').strip() for i in range(1, 4)]
    team2 = [request.form.get(f't2_m{i}', '').strip() for i in range(1, 4)]
    
    team1 = [m for m in team1 if m]
    team2 = [m for m in team2 if m]
    
    if not round_name:
        flash("Round name is required.")
        return redirect(url_for('matches'))
        
    all_submitted = team1 + team2
    real_delegates = [m for m in all_submitted if not m.startswith("SWING_")]
    
    if len(real_delegates) != len(set(real_delegates)):
        flash("Matchmaking Error: You assigned the same candidate multiple times in this single match.")
        return redirect(url_for('matches'))
        
    master = load_data()
    
    if round_name in master.get('Rounds', {}):
        for match in master['Rounds'][round_name]:
            existing_players = match['team1'] + match['team2']
            for p in real_delegates:
                if p in existing_players:
                    flash(f"Matchmaking Error: Candidate '{p}' is already scheduled in a different match for {round_name}.")
                    return redirect(url_for('matches'))
    
    if round_name not in master['Rounds']:
        master['Rounds'][round_name] = []
        
    match_id = str(uuid.uuid4())[:8]
    room = request.form.get('room', 'Unassigned')
    motion_id = request.form.get('motion_id', '')
    motion_text = ''
    if motion_id:
        all_motions = load_motions()
        found = next((m for m in all_motions if m['id'] == motion_id), None)
        if found:
            motion_text = found['text']
    
    master['Rounds'][round_name].append({
        "id": match_id,
        "is_outround": False,
        "team1": team1,
        "team2": team2,
        "status": "Pending",
        "room": room,
        "motion": motion_text,
        "winner": None
    })
    
    save_data(master)
    log_action('MATCH_CREATED', f'Created preliminary match')
    flash("Match successfully created!")
    return redirect(url_for('matches'))

@app.route('/admin/create_outround_match', methods=['POST'])
def create_outround_match():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    round_name = request.form.get('round_name')
    t1_leader = request.form.get('t1_leader')
    t2_leader = request.form.get('t2_leader')
    
    if not round_name or not t1_leader or not t2_leader:
        flash("Please complete all fields to schedule an Outround.")
        return redirect(url_for('matches'))
        
    if t1_leader == t2_leader:
        flash("A team cannot play against itself.")
        return redirect(url_for('matches'))
        
    master = load_data()
    
    # Check if team already scheduled in this round
    if round_name in master.get('Rounds', {}):
        for m in master['Rounds'][round_name]:
            if m.get('team1_leader') in [t1_leader, t2_leader] or m.get('team2_leader') in [t1_leader, t2_leader]:
                flash("One of these teams is already scheduled in this outround.")
                return redirect(url_for('matches'))
                
    if round_name not in master['Rounds']:
        master['Rounds'][round_name] = []
        
    match_id = str(uuid.uuid4())[:8]
    room = request.form.get('room', 'Unassigned')
    
    master['Rounds'][round_name].append({
        "id": match_id,
        "is_outround": True,
        "team1_leader": t1_leader,
        "team2_leader": t2_leader,
        "status": "Pending",
        "room": room,
        "winner_leader": None,
        "t1_marks": 0,
        "t2_marks": 0
    })
    
    save_data(master)
    log_action('MATCH_CREATED', f'Created outround match in {round_name}')
    flash(f"{round_name} Outround Matchup generated!")
    return redirect(url_for('matches_outrounds'))

@app.route('/admin/score/<match_id>', methods=['GET'])
def score_match_view(match_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    master = load_data()
    target_match = None
    target_round = None
    
    for r_name, m_list in master.get("Rounds", {}).items():
        for m in m_list:
            if m["id"] == match_id:
                target_match = m
                target_round = r_name
                break
                
    if not target_match:
        flash("Match not found.")
        return redirect(url_for('matches'))
        
    return render_template('score.html', match=target_match, round_name=target_round)

@app.route('/admin/submit_score/<match_id>', methods=['POST'])
def submit_score(match_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    master = load_data()
    target_match = None
    target_round = None
    
    for r_name, m_list in master.get("Rounds", {}).items():
        for m in m_list:
            if m["id"] == match_id:
                target_match = m
                target_round = r_name
                break
                
    if not target_match:
        flash("Match not found.")
        return redirect(url_for('matches'))
        
    winner_team = request.form.get('winner') # "1" or "2"
    
    # Extract marks from form
    for m in target_match['team1'] + target_match['team2']:
        if m.startswith("SWING_"): # don't track marks for swing
            continue
            
        marks = request.form.get(f'marks_{m}', '0')
        try: marks = float(marks)
        except: marks = 0.0
        master['Candidates'][m][target_round] = marks
        
    if winner_team == "1":
        for m in target_match['team1']:
            if not m.startswith("SWING_"):
                master['Candidates'][m]['Wins'] = master['Candidates'][m].get('Wins', 0) + 1
                master['Candidates'][m][f'{target_round}_win'] = 1
    elif winner_team == "2":
        for m in target_match['team2']:
            if not m.startswith("SWING_"):
                master['Candidates'][m]['Wins'] = master['Candidates'][m].get('Wins', 0) + 1
                master['Candidates'][m][f'{target_round}_win'] = 1
                
    target_match['status'] = "Completed"
    if winner_team == "1":
        target_match['winner'] = "Team 1"
    elif winner_team == "2":
        target_match['winner'] = "Team 2"
    else:
        target_match['winner'] = "Tie"
        
    save_data(master)
    log_action('MATCH_SUBMITTED', f'Submitted score for prelim match {match_id}')
    flash("Preliminary Match successfully finalized and scored!")
    return redirect(url_for('matches'))
                
@app.route('/admin/score_outround/<match_id>', methods=['GET'])
def score_outround_view(match_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    master = load_data()
    target_match = None
    target_round = None
    
    for r_name, m_list in master.get("Rounds", {}).items():
        for m in m_list:
            if m["id"] == match_id:
                target_match = m
                target_round = r_name
                break
                
    if not target_match:
        flash("Match not found.")
        return redirect(url_for('matches'))
        
    return render_template('outround_score.html', match=target_match, round_name=target_round, teams=master.get('OutroundTeams', {}))

@app.route('/admin/submit_outround_score/<match_id>', methods=['POST'])
def submit_outround_score(match_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    master = load_data()
    target_match = None
    target_round = None
    
    for r_name, m_list in master.get("Rounds", {}).items():
        for m in m_list:
            if m["id"] == match_id:
                target_match = m
                target_round = r_name
                break
                
    if not target_match:
        flash("Match not found.")
        return redirect(url_for('matches'))
        
    winner_val = request.form.get('winner') # "1" or "2"
    t1_marks = request.form.get('marks_t1', '0')
    t2_marks = request.form.get('marks_t2', '0')
    
    try: t1_marks = float(t1_marks)
    except: t1_marks = 0.0
    try: t2_marks = float(t2_marks)
    except: t2_marks = 0.0
    
    t1_leader = target_match['team1_leader']
    t2_leader = target_match['team2_leader']
    
    # Give marks to the leaders
    if t1_leader in master['Candidates']:
        master['Candidates'][t1_leader][target_round] = t1_marks
    if t2_leader in master['Candidates']:
        master['Candidates'][t2_leader][target_round] = t2_marks
        
    # Elimination Logic
    winner_name = None
    if winner_val == "1":
        winner_name = t1_leader
        if t2_leader in master['Candidates']:
            master['Candidates'][t2_leader]['Eliminated_At'] = target_round
    elif winner_val == "2":
        winner_name = t2_leader
        if t1_leader in master['Candidates']:
            master['Candidates'][t1_leader]['Eliminated_At'] = target_round
            
    target_match['status'] = "Completed"
    target_match['winner_leader'] = winner_name
    target_match['t1_marks'] = t1_marks
    target_match['t2_marks'] = t2_marks
    
    save_data(master)
    log_action('MATCH_SUBMITTED', f'Submitted score for outround match {match_id}')
    flash(f"Outround scored successfully! {'Tie recorded' if not winner_name else winner_name + ' advances'}!")
    return redirect(url_for('matches_outrounds'))

@app.route('/admin/reset_match/<match_id>', methods=['POST'])
def reset_match(match_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    master = load_data()
    target_match = None
    target_round = None
    
    for r_name, m_list in master.get("Rounds", {}).items():
        for m in m_list:
            if m["id"] == match_id:
                target_match = m
                target_round = r_name
                break
                
    if not target_match or target_match.get('status') != 'Completed':
        flash("Invalid match for reset.")
        return redirect(request.referrer or url_for('index'))
        
    hierarchy = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'Octofinals', 'Quarterfinals', 'Semifinals', 'Finals']
    if target_round in hierarchy:
        target_idx = hierarchy.index(target_round)
        for later_round in hierarchy[target_idx+1:]:
            if later_round in master.get('Rounds', {}) and len(master['Rounds'][later_round]) > 0:
                flash(f"Temporal Error: You cannot reset a {target_round} match because {later_round} has already commenced.")
                return redirect(request.referrer or url_for('index'))
                
    if target_match.get('is_outround'):
        t1 = target_match.get('team1_leader')
        t2 = target_match.get('team2_leader')
        winner = target_match.get('winner_leader')
        
        if t1 in master['Candidates'] and target_round in master['Candidates'][t1]:
            del master['Candidates'][t1][target_round]
        if t2 in master['Candidates'] and target_round in master['Candidates'][t2]:
            del master['Candidates'][t2][target_round]
            
        loser = t1 if winner == t2 else t2
        if loser and loser in master['Candidates'] and 'Eliminated_At' in master['Candidates'][loser]:
            del master['Candidates'][loser]['Eliminated_At']
            
        target_match['status'] = 'Pending'
        target_match['winner_leader'] = None
        target_match['t1_marks'] = 0
        target_match['t2_marks'] = 0
        
        save_data(master)
        log_action('MATCH_UNDONE', f'Undid outround match {match_id}')
        flash("Outround match mathematically reversed to Pending state.")
        return redirect(url_for('matches_outrounds'))
        
    else:
        winner_team_num = target_match.get('winner')
        w_team = []
        if winner_team_num == "Team 1": w_team = target_match.get('team1', [])
        elif winner_team_num == "Team 2": w_team = target_match.get('team2', [])
        
        all_players = target_match.get('team1', []) + target_match.get('team2', [])
        
        for p in all_players:
            if not p.startswith("SWING_") and p in master['Candidates']:
                if target_round in master['Candidates'][p]:
                    del master['Candidates'][p][target_round]
                    
        for p in w_team:
            if not p.startswith("SWING_") and p in master['Candidates']:
                if f'{target_round}_win' in master['Candidates'][p]:
                    del master['Candidates'][p][f'{target_round}_win']
                    master['Candidates'][p]['Wins'] = max(0, master['Candidates'][p].get('Wins', 1) - 1)
                    
        target_match['status'] = 'Pending'
        target_match['winner'] = None
        
        save_data(master)
        log_action('MATCH_UNDONE', f'Undid prelim match {match_id}')
        flash("Prelim match mathematically reversed to Pending state.")
        return redirect(url_for('matches'))
@app.route('/admin/reset_tournament', methods=['GET', 'POST'])
def reset_tournament():
    print(">>> Admin tournament reset triggered!")
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    master = load_data()
    for name, c_data in master.get('Candidates', {}).items():
        # Retain registration profile fields, wipe all scores and match results
        base = {
            'Candidate Name': c_data.get('Candidate Name'),
            'Alias': c_data.get('Alias'),
            'Class': c_data.get('Class'),
            'Level': c_data.get('Level'),
            'Institute': c_data.get('Institute'),
            'Phone': c_data.get('Phone'),
            'Notes': c_data.get('Notes'),
            'Wins': 0
        }
        if c_data.get('Avatar'):
            base['Avatar'] = c_data.get('Avatar')
        master['Candidates'][name] = base
        
    master['Rounds'] = {}
    master['OutroundTeams'] = {}
    
    save_data(master)
    log_action('RESET', 'Wiped match history (prelims)')
    flash('Tournament schedule and scores have been fully reset. The Candidate roster remains intact.')
    return redirect(url_for('matches'))

@app.route('/admin/reset_outrounds_history', methods=['GET', 'POST'])
def reset_outrounds_history():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    master = load_data()
    master['OutroundTeams'] = {}
    
    outround_keys = ['Octofinals', 'Quarterfinals', 'Semifinals', 'Finals']
    for k in outround_keys:
        if k in master.get('Rounds', {}):
            del master['Rounds'][k]
            
    for name, c_data in master.get('Candidates', {}).items():
        if 'Eliminated_At' in c_data:
            del c_data['Eliminated_At']
        for k in outround_keys:
            if k in c_data:
                del c_data[k]
            
    save_data(master)
    log_action('RESET', 'Wiped outrounds history')
    flash('Outrounds history and permanent teams have been completely wiped.')
    return redirect(url_for('matches_outrounds'))

@app.route('/admin/reset_data', methods=['POST'])
def reset_data():
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    fresh_data = {"Candidates": {}, "Rounds": {}, "OutroundTeams": {}}
    save_data(fresh_data)
    log_action('RESET', 'Factory reset active tournament database')
    flash('Hard Reset Completed! All data for the active tournament has been wiped (including Roster).')
    return redirect(url_for('index'))

@app.route('/admin/upload_avatar', methods=['POST'])
def upload_avatar():
    if not session.get('is_admin'):
        return {"success": False, "error": "Unauthorized"}, 401
        
    data = request.json
    candidate_name = data.get('candidate', '')
    image_data = data.get('image', '')
    
    if not candidate_name or not image_data:
        return {"success": False, "error": "Missing data"}, 400
        
    try:
        # Decode base64
        if ',' in image_data:
            image_data = image_data.split(',')[1]
            
        img_bytes = base64.b64decode(image_data)
        
        # Safe filename
        safe_name = "".join([c for c in candidate_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        safe_name = safe_name.replace(' ', '_').lower()
        filename = f"{safe_name}_{str(uuid.uuid4())[:6]}.png"
        
        # Ensure dir
        target_dir = os.path.join(app.root_path, 'static', 'avatars')
        os.makedirs(target_dir, exist_ok=True)
        save_path = os.path.join(target_dir, filename)
        
        with open(save_path, 'wb') as f:
            f.write(img_bytes)
            
        master = load_data()
        if candidate_name in master['Candidates']:
            # Delete old if exists (space optimization)
            old_avatar = master['Candidates'][candidate_name].get('Avatar')
            if old_avatar:
                old_path = os.path.join(target_dir, old_avatar)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            master['Candidates'][candidate_name]['Avatar'] = filename
            save_data(master)
            log_action('AVATAR_UPLOAD', f'Uploaded cropped profile picture for {candidate_name}')
            return {"success": True, "avatar_url": url_for('static', filename=f'avatars/{filename}')}
            
        return {"success": False, "error": "Candidate not found"}, 404
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admins = load_admins()
        user = next((a for a in admins if a['username'] == username), None)
        
        if user and user['password'] == password:
            session['is_admin'] = True
            session['is_master'] = (user.get('role') == 'master')
            session['admin_user'] = username
            flash(f'Successfully logged in as {username.capitalize()}.')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    session.pop('is_master', None)
    session.pop('admin_user', None)
    flash('Logged out successfully.')
    return redirect(url_for('index'))

# --- USER MANAGEMENT (MASTER ONLY) ---
@app.route('/admin/users')
def admin_users():
    if not session.get('is_master'):
        flash("You are not authorized for this action.")
        return redirect(url_for('index'))
    admins = load_admins()
    return render_template('admin_users.html', admins=admins, is_admin=True, is_master=True)

@app.route('/admin/register_admin', methods=['POST'])
def register_admin():
    if not session.get('is_master'):
        flash("Unauthorized.")
        return redirect(url_for('index'))
    
    new_user = request.form.get('username')
    new_pass = request.form.get('password')
    
    if not new_user or not new_pass:
        flash("Username and password are required.")
        return redirect(url_for('admin_users'))
        
    admins = load_admins()
    if any(a['username'] == new_user for a in admins):
        flash("User already exists.")
    else:
        admins.append({"username": new_user, "password": new_pass, "role": "admin"})
        save_admins(admins)
        log_action('SYSTEM_ADMIN', f'Added admin {new_user}')
        flash(f"Admin '{new_user}' registered successfully.")
    
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_admin/<username>', methods=['POST'])
def delete_admin(username):
    if not session.get('is_master'):
        return redirect(url_for('index'))
    
    if username == 'master':
        flash("Impossible: Cannot delete the master admin.")
        return redirect(url_for('admin_users'))
        
    admins = load_admins()
    admins = [a for a in admins if a['username'] != username]
    save_admins(admins)
    log_action('SYSTEM_ADMIN', f'Removed admin {username}')
    flash(f"User '{username}' removed.")
    return redirect(url_for('admin_users'))

# --- MOTION REPOSITORY ---
@app.route('/admin/motions')
def motion_repository():
    if not session.get('is_admin'):
        flash("Access denied. Admin only.")
        return redirect(url_for('index'))
    motions = load_motions()
    return render_template('motions.html', motions=motions, is_admin=True, is_master=session.get('is_master'), active_reveal=GLOBAL_REVEAL_STATE)

GLOBAL_REVEAL_STATE = None

@app.route('/admin/trigger_reveal/<motion_id>', methods=['POST'])
def trigger_reveal(motion_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    global GLOBAL_REVEAL_STATE
    GLOBAL_REVEAL_STATE = motion_id
    flash("Cinematic Reveal Triggered on Public Screens!")
    log_action('REVEAL_TRIGGERED', f'Fired public broadcast reveal for motion {motion_id}')
    return redirect(url_for('motion_repository'))

@app.route('/admin/clear_reveal', methods=['POST'])
def clear_reveal():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    global GLOBAL_REVEAL_STATE
    GLOBAL_REVEAL_STATE = None
    flash("Public Reveal Screen Cleared.")
    log_action('REVEAL_CLEARED', 'Cleared public broadcast reveal screen')
    return redirect(url_for('motion_repository'))

@app.route('/reveal_kiosk')
def reveal_kiosk():
    return render_template('reveal_kiosk.html')

@app.route('/api/check_reveal')
def api_check_reveal():
    global GLOBAL_REVEAL_STATE
    if not GLOBAL_REVEAL_STATE:
        return {"motion_id": None}
        
    motions = load_motions()
    target_motion = next((m for m in motions if m['id'] == GLOBAL_REVEAL_STATE and m['published']), None)
    
    if not target_motion:
        return {"motion_id": None}
        
    decoys = [
        "This house rejects the narrative of human exceptionalism",
        "This house would ban all forms of autonomous weapon systems",
        "This house regrets the commercialization of outer space",
        "This house believes that political apathy is a rational response",
        "This house would significantly restrict the collection of biometric data",
        "This house supports the implementation of a universal basic outcome",
        "This house would dismantle large-scale tech monopolies",
        "This house opposes the privatization of essential healthcare services",
        "This house believes that the UN has fundamentally failed its mandate",
        "This house regrets the dominant influence of Western philosophical traditions",
        "This house would grant legal personhood to established AI systems",
        "This house supports aggressive degrowth strategies to fight climate change",
        "This house would abolish the permanent members' veto in the UN Security Council",
        "This house believes that historical preservation stunts urban development",
        "This house would require all democratic elections to be determined by ranked-choice voting",
        "This house believes that art should never be censored for morality",
        "This house regrets the emergence of 'cancel culture' in social dynamics",
        "This house would establish a global wealth tax to fund climate reparations",
        "This house supports the mandatory break-up of all media monopolies",
        "This house believes that a benevolent dictatorship is superior to a corrupt democracy"
    ]
    import random
    random.shuffle(decoys)
    
    return {"motion_id": target_motion['id'], "text": target_motion['text'], "round": target_motion['round'], "decoys": decoys}

@app.route('/admin/motions/add', methods=['POST'])
def add_motion():
    if not session.get('is_master'):
        flash("Unauthorized.")
        return redirect(url_for('index'))
    text = request.form.get('motion_text', '').strip()
    round_name = request.form.get('round_name', '').strip()
    if not text or not round_name:
        flash("Motion text and round are required.")
        return redirect(url_for('motion_repository'))
    motions = load_motions()
    motions.append({
        'id': str(uuid.uuid4())[:8],
        'text': text,
        'round': round_name,
        'published': False
    })
    save_motions(motions)
    log_action('MOTION_DRAFTED', f'Drafted motion for {round_name}')
    flash(f"Motion saved as draft for {round_name}.")
    return redirect(url_for('motion_repository'))

@app.route('/admin/motions/publish/<motion_id>', methods=['POST'])
def publish_motion(motion_id):
    if not session.get('is_master'):
        return redirect(url_for('index'))
    motions = load_motions()
    for m in motions:
        if m['id'] == motion_id:
            m['published'] = not m['published']
            state = 'published' if m['published'] else 'unpublished'
            log_action('MOTION_PUBLISHED', f'Changed motion {motion_id} to {state}')
            flash(f"Motion {state} successfully.")
            break
    save_motions(motions)
    return redirect(url_for('motion_repository'))

@app.route('/admin/motions/delete/<motion_id>', methods=['POST'])
def delete_motion(motion_id):
    if not session.get('is_master'):
        return redirect(url_for('index'))
    motions = load_motions()
    motions = [m for m in motions if m['id'] != motion_id]
    save_motions(motions)
    log_action('MOTION_DELETED', f'Deleted motion {motion_id}')
    flash("Motion deleted.")
    return redirect(url_for('motion_repository'))

@app.route('/leaderboard/outrounds')
def leaderboard_outrounds():
    master = load_data()
    final_sorted_data = get_sorted_candidates(master)
    top_16_data = final_sorted_data[:16] 
    is_admin = session.get('is_admin', False)
    is_master = session.get('is_master', False)
    all_rounds = master.get("Rounds", {})
    return render_template('leaderboard_outrounds.html', data=top_16_data, is_admin=is_admin, is_master=is_master, rounds=all_rounds, candidates=master.get('Candidates', {}))

@app.route('/candidate/<path:name>')
def candidate_profile(name):
    master = load_data()
    candidates = master.get('Candidates', {})
    if name not in candidates:
        flash(f"Candidate '{name}' not found.")
        return redirect(url_for('index'))
    
    candidate = candidates[name]
    history = []
    
    # Compile match history from Rounds
    all_rounds = master.get("Rounds", {})
    for r_name, matches in all_rounds.items():
        if not isinstance(matches, list): continue
        for m in matches:
            is_involved = False
            opponent = "N/A"
            result = "N/A"
            marks = candidate.get(r_name, 0)
            
            if m.get('is_outround'):
                leader = candidate.get('Candidate Name')
                if m.get('team1_leader') == leader:
                    is_involved = True
                    opponent = m.get('team2_leader')
                    result = "Win" if m.get('winner_leader') == leader else ("Loss" if m.get('winner_leader') else "Pending")
                elif m.get('team2_leader') == leader:
                    is_involved = True
                    opponent = m.get('team1_leader')
                    result = "Win" if m.get('winner_leader') == leader else ("Loss" if m.get('winner_leader') else "Pending")
            else:
                leader = candidate.get('Candidate Name')
                if leader in m.get('team1', []):
                    is_involved = True
                    opponent = ", ".join(m.get('team2', []))
                    if m.get('status') == 'Completed':
                        result = "Win" if m.get('winner') == "Team 1" else ("Loss" if m.get('winner') == "Team 2" else "Tie")
                    else:
                        result = "Pending"
                elif leader in m.get('team2', []):
                    is_involved = True
                    opponent = ", ".join(m.get('team1', []))
                    if m.get('status') == 'Completed':
                        result = "Win" if m.get('winner') == "Team 2" else ("Loss" if m.get('winner') == "Team 1" else "Tie")
                    else:
                        result = "Pending"

            if is_involved:
                history.append({
                    "round": r_name,
                    "opponent": opponent,
                    "result": result,
                    "marks": marks
                })
    
    # Calculate Totals
    prelims_keys = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6']
    outrounds_keys = ['Octofinals', 'Quarterfinals', 'Semifinals', 'Finals']
    
    prelim_total = 0.0
    for k in prelims_keys:
        try: prelim_total += float(candidate.get(k, 0))
        except: pass
        
    outround_total = 0.0
    highest_outround = "Preliminaries"
    for k in outrounds_keys:
        val = candidate.get(k, 0)
        try: 
            mark = float(val)
            if mark > 0:
                outround_total += mark
                highest_outround = k
        except: pass
        if candidate.get(f"{k}_win") or candidate.get('Eliminated_At') == k:
            highest_outround = k

    # Add calculated fields to the candidate object for the template
    candidate['PrelimTotal'] = f"{prelim_total:.2f}"
    candidate['OutroundTotal'] = f"{outround_total:.2f}"
    candidate['HighestStage'] = highest_outround
    
    return render_template('candidate_profile.html', candidate=candidate, history=history, is_admin=session.get('is_admin'))

@app.route('/live')
def live_dashboard():
    master = load_data()
    final_sorted_data = get_sorted_candidates(master)
    all_rounds = master.get("Rounds", {})
    
    # Get current active/pending matches
    raw_active_matches = []
    is_outrounds = False
    for r_name, matches in all_rounds.items():
        if r_name in ['Octofinals', 'Quarterfinals', 'Semifinals', 'Finals'] and matches:
            # If any outround match exists (even if completed), we are fundamentally in outrounds phase
            is_outrounds = True
        
        if not isinstance(matches, list): continue
        for m in matches:
            if m.get('status') == 'Pending':
                raw_active_matches.append({**m, "round": r_name, "is_outround": r_name in ['Octofinals', 'Quarterfinals', 'Semifinals', 'Finals']})
                
    # Strictly isolate matches based on tournament phase
    if is_outrounds:
        active_matches = [m for m in raw_active_matches if m['is_outround']]
    else:
        active_matches = [m for m in raw_active_matches if not m['is_outround']]
        
    return render_template('live_dashboard.html', 
                           all_candidates=final_sorted_data, 
                           active_matches=active_matches,
                           is_outrounds=is_outrounds)

# --- TIMER ROUTES ---
@app.route('/timer')
def global_timer():
    is_admin = session.get('is_admin', False)
    is_master = session.get('is_master', False)
    return render_template('timer.html', is_admin=is_admin, is_master=is_master, presets=load_timer_presets())

@app.route('/api/timer')
def api_timer():
    return json.dumps(load_timer_presets())

import time

@app.route('/admin/timer/add_preset', methods=['POST'])
def add_timer_preset():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    presets = load_timer_presets()
    name = request.form.get('preset_name', 'Custom Timer').strip()
    duration_mins = request.form.get('duration_mins', '5')
    bell1_mins = request.form.get('bell1_mins', '1')
    bell2_mins = request.form.get('bell2_mins', '0')
    
    try:
        d_sec = int(float(duration_mins) * 60)
        b1_sec = int(float(bell1_mins) * 60)
        b2_sec = int(float(bell2_mins) * 60)
        presets.append({
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "duration": d_sec,
            "bells": sorted(list(set([b1_sec, b2_sec])), reverse=True)
        })
        save_timer_presets(presets)
        log_action('TIMER_ADDED', f'Created timer preset: {name}')
        flash(f"Timer preset '{name}' created.")
    except:
        flash("Invalid timer configuration.")
        
    return redirect(url_for('global_timer'))

@app.route('/admin/timer/delete_preset/<preset_id>', methods=['POST'])
def delete_timer_preset(preset_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    presets = load_timer_presets()
    presets = [p for p in presets if p.get('id') != preset_id]
    save_timer_presets(presets)
    log_action('TIMER_DELETED', f'Deleted timer preset {preset_id}')
    flash("Timer preset deleted.")
    return redirect(url_for('global_timer'))

# --- AUDIT ROUTES ---
@app.route('/admin/audit')
def audit_view():
    if not session.get('is_master'):
        return redirect(url_for('index'))
    logs = load_audit()
    return render_template('audit_log.html', logs=logs, is_admin=True, is_master=True)

@app.route('/admin/audit/print')
def audit_print():
    if not session.get('is_master'):
        return redirect(url_for('index'))
    logs = load_audit()
    return render_template('audit_print.html', logs=logs)

@app.route('/admin/audit/clear', methods=['POST'])
def audit_clear():
    if not session.get('is_master'):
        return redirect(url_for('index'))
    save_audit([])
    log_action('AUDIT_CLEARED', 'Logs were permanently cleared by Master')
    flash("Audit logs successfully cleared.")
    return redirect(url_for('audit_view'))


# --- ARCHIVE & SETTINGS ROUTES ---

@app.route('/admin/settings')
def admin_settings():
    if not session.get('is_master'):
        return redirect(url_for('index'))
    archives = load_archives_index()
    t_index = load_tournaments_index()
    tournaments = t_index.get("tournaments", [])
    active_tournament_id = t_index.get("active_id")
    return render_template('admin_settings.html', is_admin=True, is_master=True, archives=archives, tournaments=tournaments, active_tournament_id=active_tournament_id)

# --- TOURNAMENT WORKSPACE ROUTES ---

@app.route('/admin/tournaments/create', methods=['POST'])
def tournament_create():
    if not session.get('is_master'):
        return redirect(url_for('index'))

    name = request.form.get('tournament_name', '').strip()
    if not name:
        flash("Tournament name is required.", "error")
        return redirect(url_for('admin_settings'))

    tournament_id = str(uuid.uuid4())[:8]
    dest = os.path.join(TOURNAMENTS_DIR, f"{tournament_id}.json")
    with open(dest, 'w', encoding='utf-8') as f:
        json.dump({"Candidates": {}, "Rounds": {}, "OutroundTeams": {}}, f, indent=4)

    index = load_tournaments_index()
    index["tournaments"].append({
        "id": tournament_id,
        "name": name,
        "created": datetime.datetime.now().strftime("%Y-%m-%d"),
        "status": "inactive"
    })
    save_tournaments_index(index)

    log_action('TOURNAMENT_CREATED', f'Created new tournament workspace: "{name}"')
    flash(f"Tournament '{name}' created. Activate it to make it live.", "success")
    return redirect(url_for('admin_settings'))

@app.route('/admin/tournaments/<tournament_id>/activate', methods=['POST'])
def tournament_activate(tournament_id):
    if not session.get('is_master'):
        return redirect(url_for('index'))

    index = load_tournaments_index()
    target = next((t for t in index["tournaments"] if t["id"] == tournament_id), None)
    if not target:
        flash("Tournament not found.", "error")
        return redirect(url_for('admin_settings'))

    for t in index["tournaments"]:
        if t["id"] == index.get("active_id") and t["status"] == "active":
            t["status"] = "inactive"

    index["active_id"] = tournament_id
    target["status"] = "active"
    save_tournaments_index(index)

    log_action('TOURNAMENT_ACTIVATED', f'Switched active tournament to "{target["name"]}"')
    flash(f"'{target['name']}' is now the live tournament.", "success")
    return redirect(url_for('admin_settings'))

@app.route('/admin/tournaments/<tournament_id>/delete', methods=['POST'])
def tournament_delete(tournament_id):
    if not session.get('is_master'):
        return redirect(url_for('index'))

    index = load_tournaments_index()

    if index.get("active_id") == tournament_id:
        flash("Cannot delete the currently active tournament. Activate a different tournament first.", "error")
        return redirect(url_for('admin_settings'))

    target = next((t for t in index["tournaments"] if t["id"] == tournament_id), None)
    if not target:
        flash("Tournament not found.", "error")
        return redirect(url_for('admin_settings'))

    dest = os.path.join(TOURNAMENTS_DIR, f"{tournament_id}.json")
    if os.path.exists(dest):
        os.remove(dest)

    index["tournaments"] = [t for t in index["tournaments"] if t["id"] != tournament_id]
    save_tournaments_index(index)

    log_action('TOURNAMENT_DELETED', f'Deleted tournament workspace: "{target["name"]}"')
    flash(f"Tournament '{target['name']}' has been permanently deleted.", "success")
    return redirect(url_for('admin_settings'))

@app.route('/admin/archive/create', methods=['POST'])
def archive_create():
    if not session.get('is_master'):
        return redirect(url_for('index'))

    name = request.form.get('archive_name', '').strip()
    if not name:
        flash("Archive name is required.", "error")
        return redirect(url_for('admin_settings'))

    archive_id = str(uuid.uuid4())[:8]
    archive_filepath = os.path.join(ARCHIVE_DIR, f"{archive_id}.json")

    # Snapshot the current active tournament data
    master_data = load_data()
    master_data['Motions'] = load_motions()
    master_data['TimerPresets'] = load_timer_presets()

    with open(archive_filepath, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, indent=4)

    # Update the Hall of Fame archives index
    archives = load_archives_index()
    archives.insert(0, {
        "id": archive_id,
        "name": name,
        "date": datetime.datetime.now().strftime("%Y-%m-%d")
    })
    save_archives_index(archives)

    log_action('ARCHIVE_CREATED', f'Archived current tournament as "{name}"')

    # Mark the current workspace as archived in the tournament index
    t_index = load_tournaments_index()
    current_id = t_index.get("active_id")
    for t in t_index["tournaments"]:
        if t["id"] == current_id:
            t["status"] = "archived"
            break

    # Create a fresh new tournament workspace and activate it
    new_id = str(uuid.uuid4())[:8]
    new_path = os.path.join(TOURNAMENTS_DIR, f"{new_id}.json")
    with open(new_path, 'w', encoding='utf-8') as f:
        json.dump({"Candidates": {}, "Rounds": {}, "OutroundTeams": {}}, f, indent=4)

    t_index["tournaments"].insert(0, {
        "id": new_id,
        "name": "New Tournament",
        "created": datetime.datetime.now().strftime("%Y-%m-%d"),
        "status": "active"
    })
    t_index["active_id"] = new_id
    save_tournaments_index(t_index)

    save_motions([])
    log_action('TOURNAMENT_CREATED', 'Auto-created new tournament workspace after archiving')
    flash(f"Tournament archived as '{name}'. A fresh workspace is now live — rename it in Tournament Workspaces.", "success")
    return redirect(url_for('admin_settings'))

@app.route('/admin/archive/delete/<archive_id>', methods=['POST'])
def archive_delete(archive_id):
    if not session.get('is_master'):
        return redirect(url_for('index'))
        
    archives = load_archives_index()
    
    archives = [a for a in archives if a.get('id') != archive_id]
    save_archives_index(archives)
    
    archive_filepath = os.path.join(ARCHIVE_DIR, f"{archive_id}.json")
    if os.path.exists(archive_filepath):
        os.remove(archive_filepath)
        
    log_action('ARCHIVE_DELETED', f'Deleted archive {archive_id}')
    flash("Historical archive deleted permanently.", "success")
    return redirect(url_for('admin_settings'))

@app.route('/hall_of_fame')
def hall_of_fame():
    archives = load_archives_index()
    return render_template('hall_of_fame.html', archives=archives, is_admin=session.get('is_admin'), is_master=session.get('is_master'))

@app.route('/hall_of_fame/<archive_id>')
def hall_of_fame_view(archive_id):
    archives = load_archives_index()
    archive_meta = next((a for a in archives if a.get('id') == archive_id), None)
    
    if not archive_meta:
        flash("Archive not found.")
        return redirect(url_for('hall_of_fame'))
        
    archive_filepath = os.path.join(ARCHIVE_DIR, f"{archive_id}.json")
    if not os.path.exists(archive_filepath):
        flash("Archive data file missing.")
        return redirect(url_for('hall_of_fame'))
        
    with open(archive_filepath, 'r', encoding='utf-8') as f:
        master_data = json.load(f)
        
    candidates = get_sorted_candidates(master_data)
    
    return render_template('hall_of_fame_view.html', 
        archive_meta=archive_meta,
        candidates=candidates,
        data=master_data,
        is_admin=session.get('is_admin'), 
        is_master=session.get('is_master')
    )

@app.route('/hall_of_fame/<archive_id>/candidate/<path:name>')
def hall_of_fame_candidate(archive_id, name):
    archives = load_archives_index()
    archive_meta = next((a for a in archives if a.get('id') == archive_id), None)
    
    if not archive_meta:
        flash("Archive not found.")
        return redirect(url_for('hall_of_fame'))
        
    archive_filepath = os.path.join(ARCHIVE_DIR, f"{archive_id}.json")
    if not os.path.exists(archive_filepath):
        flash("Archive data file missing.")
        return redirect(url_for('hall_of_fame'))
        
    with open(archive_filepath, 'r', encoding='utf-8') as f:
        master_data = json.load(f)
        
    candidates = master_data.get('Candidates', {})
    if name not in candidates:
        flash(f"Candidate '{name}' not found in archive.")
        return redirect(url_for('hall_of_fame_view', archive_id=archive_id))
        
    candidate = candidates[name]
    history = []
    
    all_rounds = master_data.get("Rounds", {})
    for r_name, matches in all_rounds.items():
        if not isinstance(matches, list): continue
        for m in matches:
            is_involved = False
            opponent = "N/A"
            result = "N/A"
            marks = candidate.get(r_name, 0)
            
            if m.get('is_outround'):
                leader = candidate.get('Candidate Name')
                if m.get('team1_leader') == leader:
                    is_involved = True
                    opponent = m.get('team2_leader')
                    result = "Win" if m.get('winner_leader') == leader else ("Loss" if m.get('winner_leader') else "Pending")
                elif m.get('team2_leader') == leader:
                    is_involved = True
                    opponent = m.get('team1_leader')
                    result = "Win" if m.get('winner_leader') == leader else ("Loss" if m.get('winner_leader') else "Pending")
            else:
                leader = candidate.get('Candidate Name')
                if leader in m.get('team1', []):
                    is_involved = True
                    opponent = ", ".join(m.get('team2', []))
                    if m.get('status') == 'Completed':
                        result = "Win" if m.get('winner') == "Team 1" else ("Loss" if m.get('winner') == "Team 2" else "Tie")
                    else:
                        result = "Pending"
                elif leader in m.get('team2', []):
                    is_involved = True
                    opponent = ", ".join(m.get('team1', []))
                    if m.get('status') == 'Completed':
                        result = "Win" if m.get('winner') == "Team 2" else ("Loss" if m.get('winner') == "Team 1" else "Tie")
                    else:
                        result = "Pending"

            if is_involved:
                history.append({
                    "round": r_name,
                    "opponent": opponent,
                    "result": result,
                    "marks": marks
                })
    
    prelims_keys = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6']
    outrounds_keys = ['Octofinals', 'Quarterfinals', 'Semifinals', 'Finals']
    
    prelim_total = 0.0
    for k in prelims_keys:
        try: prelim_total += float(candidate.get(k, 0))
        except: pass
        
    outround_total = 0.0
    highest_outround = "Prelims"
    for k in outrounds_keys:
        try: 
            mark = float(candidate.get(k, 0))
            if mark > 0:
                outround_total += mark
                highest_outround = k
        except: pass
        if candidate.get(f"{k}_win") or candidate.get('Eliminated_At') == k:
            highest_outround = k

    candidate['PrelimTotal'] = f"{prelim_total:.2f}"
    candidate['OutroundTotal'] = f"{outround_total:.2f}"
    candidate['HighestStage'] = highest_outround
    
    return render_template('candidate_profile.html', candidate=candidate, history=history, is_admin=False, archive_meta=archive_meta)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)

