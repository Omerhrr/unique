# backend/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select, text
import os

from pathlib import Path 
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
from typing import Optional
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timedelta
# Core application imports

from .core import * 
from .admin import *

BACKEND_DIR = Path(__file__).parent 
# This will be the absolute path to your project's root folder
BASE_DIR = BACKEND_DIR.parent 
# This is the absolute path to your 'frontend' folder
FRONTEND_DIR = BASE_DIR / "frontend"

load_dotenv()
app = FastAPI(title="Unique Sale Airdrop")

app.include_router(router, prefix="/admin", tags=["Admin"])

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    with Session(engine) as session: # Make sure you have 'engine' defined from create_db_and_tables

        if not session.exec(select(Task)).first():
            print("No tasks found, creating default tasks...")
            default_tasks = [
                Task(name="Follow on X", description="Follow our official X account", points=5000, link="https://x.com/uniquesale_fin", icon="twitter" ),
                Task(name="Join Telegram", description="Join our community Telegram channel", points=5000, link="https://t.me/uniquesalefinance", icon="telegram" ),
                Task(name="Subscribe to YouTube", description="Subscribe to our YouTube channel", points=3000, link="https://youtube.com/your_channel", icon="youtube" ),
            ]
            for task in default_tasks:
                session.add(task)
            session.commit()
            print("Default tasks created.")


class UserDataResponse(BaseModel):
    score: int
    walletAddress: Optional[str]
    game_sessions: int
    max_sessions: int
    tap_level: int
    username: Optional[str] # Add this
    claimable_rewards: int = 0 # Add this
    referral_code: str

class SyncRequest(BaseModel):
    taps: int



class GameResult(BaseModel):
    points_earned: int


def get_tap_level(score: int) -> int:
    """Calculates the user's tap level based on their score."""
    if score >= 5000:
        return 10
    if score >= 1000:
        return 5
    if score >= 300:
        return 3
    if score >= 100:
        return 2
    return 1


@app.get("/")
async def read_root():
    html_file_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    return FileResponse(html_file_path)



@app.post("/claim_rewards", response_model=UserDataResponse)
def claim_rewards(
    validated_data: dict = Depends(get_validated_data),
    session: Session = Depends(get_session)
):
    user_id = validated_data['user']['id']
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Recalculate rewards to ensure accuracy at the moment of claiming
    time_since_last_claim = datetime.utcnow() - db_user.last_claim_time
    claimable_rewards = int(time_since_last_claim.total_seconds() * (db_user.farming_rate / 3600))

    if claimable_rewards > 0:
        db_user.score += claimable_rewards
        db_user.last_claim_time = datetime.utcnow() # Reset the claim timer
        session.add(db_user)
        session.commit()
        session.refresh(db_user)

    # Return the full, updated user state
    return UserDataResponse(
        score=db_user.score,
        walletAddress=db_user.wallet_address,
        game_sessions=db_user.game_sessions,
        max_sessions=MAX_SESSIONS,
        tap_level=get_tap_level(db_user.score),
        username=db_user.username,
        claimable_rewards=0,
        referral_code=db_user.referral_code
    )


class WalletSaveRequest(BaseModel):
    wallet_address: str


@app.post("/save_wallet", response_model=UserDataResponse)
def save_wallet(
    request: WalletSaveRequest,
    validated_data: dict = Depends(get_validated_data),
    session: Session = Depends(get_session)
):
    user_id = validated_data['user']['id']
    user = session.get(User, user_id) # The variable is 'user'
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not (32 <= len(request.wallet_address) <= 44):
        raise HTTPException(status_code=400, detail="Invalid Solana address format.")

    user.wallet_address = request.wallet_address
    session.add(user)
    session.commit()
    session.refresh(user)

    # --- THIS IS THE FIX ---
    # The variable name has been corrected from 'db_user' to 'user'
    return UserDataResponse(
        score=user.score,
        walletAddress=user.wallet_address,
        game_sessions=user.game_sessions,
        max_sessions=MAX_SESSIONS,
        tap_level=get_tap_level(user.score),
        username=user.username,
        claimable_rewards=0, # Claimable rewards don't change here, so return 0 or recalculate if needed
        referral_code=user.referral_code # Corrected from db_user.referral_code
    )



@app.post("/submit_game_score")
def submit_game_score(
    result: GameResult,
    *,
    session: Session = Depends(get_session),
    validated_data: dict = Depends(get_validated_data)
):
    user_id = validated_data.get('user', {}).get('id')
    db_user = session.get(User, user_id)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")
    

    if db_user.game_sessions <= 0:
        raise HTTPException(status_code=403, detail="No game sessions left.")

    db_user.game_sessions -= 1
    db_user.score += result.points_earned

    if db_user.score >= 5000:
        db_user.tap_level = 10
    elif db_user.score >= 1000:
        db_user.tap_level = 5
    elif db_user.score >= 300:
        db_user.tap_level = 3
    elif db_user.score >= 100:
        db_user.tap_level = 2
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return {"status": "success", "new_score": db_user.score, "sessions_left": db_user.game_sessions}


# In backend/main.py, replace the whole function

@app.get("/get_user_data", response_model=UserDataResponse)
def get_user_data(validated_data: dict = Depends(get_validated_data), session: Session = Depends(get_session)):
    user_data = validated_data.get('user', {})
    user_id = user_data.get('id')
    
    # Use 'db_user' consistently
    db_user = session.get(User, user_id)

    if not db_user:
        # This is a new user
        print(f"First time user {user_id}. Creating entry.")
        
        # --- NEW: Handle referral ---
        referrer_id = None
        referral_code_used = user_data.get('referral_code_used')
        if referral_code_used:
            referrer = session.exec(select(User).where(User.referral_code == referral_code_used)).first()
            if referrer:
                referrer_id = referrer.id
                # Award bonus to the referrer
                referrer.score += 10000 # Example: 10,000 point bonus
                session.add(referrer)
                print(f"Awarded 10,000 points to referrer {referrer_id}")
        db_user = User(
            id=user_id,
            first_name=user_data.get('first_name'),
            last_name=user_data.get('last_name'),
            username=user_data.get('username'),
            score=0,
            game_sessions=MAX_SESSIONS,
            last_session_recharge=datetime.utcnow(),
            tap_level=1,
            referred_by_id=referrer_id,

        )
        session.add(db_user)
    else:

        if (db_user.username != user_data.get('username') or 
            db_user.first_name != user_data.get('first_name')):
            db_user.username = user_data.get('username')
            db_user.first_name = user_data.get('first_name')
            session.add(db_user)

        # Recharge game sessions based on time passed
        time_passed = datetime.utcnow() - db_user.last_session_recharge
        # Assuming 1 session recharges every 10 minutes (600 seconds)
        sessions_to_add = int(time_passed.total_seconds() / 600) 
        if sessions_to_add > 0:
            db_user.game_sessions = min(db_user.game_sessions + sessions_to_add, MAX_SESSIONS)
            # Reset the recharge timer
            db_user.last_session_recharge = datetime.utcnow()
            session.add(db_user)
    time_since_last_claim = datetime.utcnow() - db_user.last_claim_time
    # Calculate rewards earned in seconds, then convert to a whole number
    # User's farming_rate is per hour, so we divide by 3600 to get per-second rate
    claimable_rewards = int(time_since_last_claim.total_seconds() * (db_user.farming_rate / 3600))


    session.commit()
    session.refresh(db_user)

    # --- THIS IS THE FIX ---
    # Use the correct 'db_user' variable here
    return UserDataResponse(
        score=db_user.score,
        walletAddress=db_user.wallet_address,
        game_sessions=db_user.game_sessions,
        max_sessions=MAX_SESSIONS,
        tap_level=get_tap_level(db_user.score), # Use the helper function
        username=db_user.username,
        claimable_rewards= claimable_rewards,
        referral_code=db_user.referral_code
    )

 
@app.post("/sync_score", response_model=UserDataResponse)
def sync_score(
    sync_request: SyncRequest,
    *,
    session: Session = Depends(get_session),
    validated_data: dict = Depends(get_validated_data)
):
    user_data = validated_data.get('user', {})
    user_id = user_data.get('id')
    db_user = session.get(User, user_id)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found during sync")

    if db_user.game_sessions > 0:
        db_user.game_sessions -= 1

    db_user.score += sync_request.taps

    if db_user.score >= 5000:
        db_user.tap_level = 10
    elif db_user.score >= 1000:
        db_user.tap_level = 5
    elif db_user.score >= 300:
        db_user.tap_level = 3
    elif db_user.score >= 100:
        db_user.tap_level = 2
    else:
        db_user.tap_level = 1
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return UserDataResponse(
        score=db_user.score,
        walletAddress=db_user.wallet_address,
        game_sessions=db_user.game_sessions,
        max_sessions=MAX_SESSIONS,
        tap_level=get_tap_level(db_user.score), # Use the helper function for consistency
        username=db_user.username,
        claimable_rewards=0 ,
        referral_code=db_user.referral_code
    )




# In backend/main.py, add these Pydantic models at the top with the others

class LeaderboardUser(BaseModel):
    rank: int
    username: Optional[str]
    score: int

class LeaderboardResponse(BaseModel):
    top_users: list[LeaderboardUser]
    current_user_rank: Optional[int]


# Now, find the @app.get("/leaderboard") endpoint and REPLACE it entirely with this new version:

@app.get("/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(
    *,
    session: Session = Depends(get_session),
    validated_data: dict = Depends(get_validated_data)
):
    user_id = validated_data.get('user', {}).get('id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user data")

    # Get top 10 users
    top_users_statement = select(User).order_by(User.score.desc()).limit(10)
    top_users_result = session.exec(top_users_statement).all()

    top_users_list = [
        LeaderboardUser(rank=i + 1, username=user.username or user.first_name, score=user.score)
        for i, user in enumerate(top_users_result)
    ]

    # Get current user's rank
    user_rank = None
    try:
        # Use a window function to get the rank of all users
        rank_query = text(
            "SELECT rank FROM (SELECT id, RANK() OVER (ORDER BY score DESC) as rank FROM user) as ranked_users WHERE id = :user_id"
        )
        user_rank_row = session.exec(rank_query, params={"user_id": user_id}).first()
        if user_rank_row:
            user_rank = user_rank_row[0]
    except Exception as e:
        print(f"Could not retrieve user rank: {e}")
        # This is not critical, so we can fail gracefully
        user_rank = None

    return LeaderboardResponse(top_users=top_users_list, current_user_rank=user_rank)



# In backend/main.py, add these new Pydantic and API endpoints

class TaskResponse(BaseModel):
    id: int
    name: str
    description: str
    points: int
    link: str
    icon: str
    completed: bool

@app.get("/tasks", response_model=list[TaskResponse])
def get_tasks(
    validated_data: dict = Depends(get_validated_data),
    session: Session = Depends(get_session)
):
    user_id = validated_data['user']['id']
    all_tasks = session.exec(select(Task)).all()
    completed_tasks_statement = select(UserTask).where(UserTask.user_id == user_id)
    completed_tasks = session.exec(completed_tasks_statement).all()
    completed_task_ids = {ut.task_id for ut in completed_tasks}

    response = []
    for task in all_tasks:
        response.append(TaskResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            points=task.points,
            link=task.link,
            icon=task.icon,
            completed=(task.id in completed_task_ids)
        ))
    return response

@app.post("/claim_task/{task_id}", response_model=TaskResponse)
def claim_task(
    task_id: int,
    validated_data: dict = Depends(get_validated_data),
    session: Session = Depends(get_session)
):
    user_id = validated_data['user']['id']
    
    # Check if task exists
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if user has already completed this task
    existing_completion = session.get(UserTask, (user_id, task_id))
    if existing_completion:
        raise HTTPException(status_code=400, detail="Task already completed")

    # Mark task as completed
    user_task = UserTask(user_id=user_id, task_id=task_id)
    session.add(user_task)

    # Award points to the user
    user = session.get(User, user_id)
    user.score += task.points
    session.add(user)
    
    session.commit()
    session.refresh(user)

    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        points=task.points,
        link=task.link,
        icon=task.icon,
        completed=True
    )

# In backend/main.py

class FriendResponse(BaseModel):
    username: Optional[str]
    score: int

@app.get("/friends", response_model=list[FriendResponse])
def get_friends(
    validated_data: dict = Depends(get_validated_data),
    session: Session = Depends(get_session)
):
    user_id = validated_data['user']['id']
    
    # Find all users who have the current user's ID as their 'referred_by_id'
    friends_statement = select(User).where(User.referred_by_id == user_id)
    friends = session.exec(friends_statement).all()
    
    return [FriendResponse(username=f.username or f.first_name, score=f.score) for f in friends]



@app.get("/")
async def read_index():

    return FileResponse(FRONTEND_DIR / "index.html")

app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")


