from fastapi import Depends
from gnom_hub.db.agent_repo import SQLiteAgentRepository as AR
from gnom_hub.db.chat_repo import SQLiteChatRepository as CR
from gnom_hub.infrastructure.llm.orchestrator import LLMOrchestrator as LO
from gnom_hub.infrastructure.process.process_manager import ProcessManager as PM
from gnom_hub.infrastructure.admin.service import AdminService as AS
from gnom_hub.agents.commands import AgentCommands as AC
from gnom_hub.agents.queries import AgentQueries as AQ
from gnom_hub.chat.service import ChatService as CS
from gnom_hub.chat.send_message import SendMessageUseCase as SM
from gnom_hub.chat.brainstorm import BrainstormUseCase as BS

# Singletons & Services
def get_agent_repo(): return AR()
def get_chat_repo(): return CR()
def get_process_manager(): return PM()
def get_llm_orchestrator(): return LO()
def get_admin_service(): return AS()

def get_agent_commands(repo=Depends(get_agent_repo), pm=Depends(get_process_manager)):
    return AC(repo, pm)

def get_agent_queries(repo=Depends(get_agent_repo)):
    return AQ(repo)

def get_send_message_use_case(chat_repo=Depends(get_chat_repo), agent_repo=Depends(get_agent_repo), llm=Depends(get_llm_orchestrator)):
    return SM(chat_repo, agent_repo, llm)

def get_brainstorm_use_case(repo=Depends(get_agent_repo), llm=Depends(get_llm_orchestrator)):
    return BS(repo, llm)

def get_chat_service(send_uc=Depends(get_send_message_use_case), brainstorm_uc=Depends(get_brainstorm_use_case)):
    return CS(send_uc, brainstorm_uc)
