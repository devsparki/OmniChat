from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import socketio
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Socket.IO setup
sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# AI Chat setup
def get_ai_chat(session_id: str):
    return LlmChat(
        api_key=os.environ.get('EMERGENT_LLM_KEY'),
        session_id=session_id,
        system_message="You are an AI assistant in OmniChat. Provide helpful, concise responses for real-time chat. Keep responses brief and conversational."
    ).with_model("openai", "gpt-5")

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    avatar_url: Optional[str] = None
    status: str = "offline"  # online, offline, typing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    username: str
    email: str
    avatar_url: Optional[str] = None

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    sender_username: str
    content: str
    message_type: str = "text"  # text, ai_response, system
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    conversation_id: str

class MessageCreate(BaseModel):
    content: str
    sender_id: str
    sender_username: str
    conversation_id: str
    message_type: str = "text"

class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    participants: List[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_message: Optional[str] = None
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConversationCreate(BaseModel):
    name: str
    participants: List[str]

# Helper functions
def prepare_for_mongo(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    if isinstance(item, dict):
        for key, value in item.items():
            if key.endswith('_at') and isinstance(value, str):
                try:
                    item[key] = datetime.fromisoformat(value)
                except:
                    pass
    return item

# API Routes
@api_router.get("/")
async def root():
    return {"message": "OmniChat API is running!"}

@api_router.post("/users", response_model=User)
async def create_user(user_data: UserCreate):
    user = User(**user_data.dict())
    user_dict = prepare_for_mongo(user.dict())
    await db.users.insert_one(user_dict)
    return user

@api_router.get("/users", response_model=List[User])
async def get_users():
    users = await db.users.find().to_list(1000)
    return [User(**parse_from_mongo(user)) for user in users]

@api_router.put("/users/{user_id}/status")
async def update_user_status(user_id: str, status: str):
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"status": status}}
    )
    await sio.emit('user_status_changed', {"user_id": user_id, "status": status})
    return {"success": True}

@api_router.post("/conversations", response_model=Conversation)
async def create_conversation(conv_data: ConversationCreate):
    conversation = Conversation(**conv_data.dict())
    conv_dict = prepare_for_mongo(conversation.dict())
    await db.conversations.insert_one(conv_dict)
    return conversation

@api_router.get("/conversations", response_model=List[Conversation])
async def get_conversations():
    conversations = await db.conversations.find().to_list(1000)
    return [Conversation(**parse_from_mongo(conv)) for conv in conversations]

@api_router.get("/conversations/{conversation_id}/messages", response_model=List[Message])
async def get_messages(conversation_id: str):
    messages = await db.messages.find({"conversation_id": conversation_id}).to_list(1000)
    return [Message(**parse_from_mongo(msg)) for msg in messages]

@api_router.post("/messages", response_model=Message)
async def create_message(msg_data: MessageCreate):
    message = Message(**msg_data.dict())
    msg_dict = prepare_for_mongo(message.dict())
    await db.messages.insert_one(msg_dict)
    
    # Update conversation last activity
    await db.conversations.update_one(
        {"id": msg_data.conversation_id},
        {"$set": {
            "last_message": msg_data.content[:50] + "..." if len(msg_data.content) > 50 else msg_data.content,
            "last_activity": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Emit to all users in conversation
    await sio.emit('new_message', message.dict(), room=msg_data.conversation_id)
    return message

@api_router.post("/ai/chat")
async def ai_chat_response(msg_data: MessageCreate):
    try:
        # Get AI response
        ai_chat = get_ai_chat(msg_data.conversation_id)
        user_message = UserMessage(text=msg_data.content)
        ai_response = await ai_chat.send_message(user_message)
        
        # Create AI message
        ai_msg = Message(
            sender_id="ai-assistant",
            sender_username="AI Assistant",
            content=ai_response,
            message_type="ai_response",
            conversation_id=msg_data.conversation_id
        )
        
        ai_msg_dict = prepare_for_mongo(ai_msg.dict())
        await db.messages.insert_one(ai_msg_dict)
        
        # Update conversation
        await db.conversations.update_one(
            {"id": msg_data.conversation_id},
            {"$set": {
                "last_message": "AI: " + (ai_response[:50] + "..." if len(ai_response) > 50 else ai_response),
                "last_activity": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Emit AI response
        await sio.emit('new_message', ai_msg.dict(), room=msg_data.conversation_id)
        return ai_msg
        
    except Exception as e:
        logging.error(f"AI chat error: {str(e)}")
        return {"error": "AI response failed"}

# Socket.IO Events
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event
async def join_conversation(sid, data):
    conversation_id = data.get('conversation_id')
    if conversation_id:
        await sio.enter_room(sid, conversation_id)
        await sio.emit('joined_conversation', {"conversation_id": conversation_id}, room=sid)

@sio.event
async def leave_conversation(sid, data):
    conversation_id = data.get('conversation_id')
    if conversation_id:
        await sio.leave_room(sid, conversation_id)

@sio.event
async def typing_start(sid, data):
    conversation_id = data.get('conversation_id')
    user_id = data.get('user_id')
    username = data.get('username')
    if conversation_id:
        await sio.emit('user_typing', {
            "user_id": user_id,
            "username": username,
            "typing": True
        }, room=conversation_id, skip_sid=sid)

@sio.event
async def typing_stop(sid, data):
    conversation_id = data.get('conversation_id')
    user_id = data.get('user_id')
    if conversation_id:
        await sio.emit('user_typing', {
            "user_id": user_id,
            "typing": False
        }, room=conversation_id, skip_sid=sid)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create Socket.IO app that wraps FastAPI
socket_app = socketio.ASGIApp(sio, app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()