import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func, or_, and_, text
from sqlalchemy.orm import sessionmaker
from backend.telegram_analyzer import TelegramMessage, MessageSearch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('message_retriever.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MessageRetriever')

class MessageRetriever:
    def __init__(self, db_path: str = 'telegram_messages.db'):
        self.engine = create_engine(f'sqlite:///{db_path}')
        self.Session = sessionmaker(bind=self.engine)
    
    def optimize_keywords_for_length(
        self,
        chat_id: str,
        keywords: List[str],
        start_date: datetime,
        end_date: datetime,
        max_length: int = 10000,
        existing_stats: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Optimize the keyword set to produce messages within the specified character limit.
        Removes keywords from the end of the list until the total length is under the limit.
        
        Args:
            chat_id: ID of the chat to search in
            keywords: List of keywords sorted by relevance (most relevant first)
            start_date: Start date for the search
            end_date: End date for the search
            max_length: Maximum total length of messages to retrieve
            existing_stats: Optional dictionary containing existing message statistics
            
        Returns:
            Optimized list of keywords that will produce messages within the length limit
        """
        try:
            # Start with all keywords
            current_keywords = keywords.copy()
            
            if existing_stats and 'keyword_messages' in existing_stats:
                # Use existing statistics
                total_length = existing_stats['keyword_messages']['total_length']
                keyword_stats = existing_stats['keyword_messages']['by_keyword']
                
                # Remove keywords from the end until we're under the limit
                while total_length > max_length and len(current_keywords) > 1:
                    # Remove the last keyword
                    removed_keyword = current_keywords.pop()
                    
                    # Update total length using existing statistics
                    if removed_keyword in keyword_stats:
                        total_length -= keyword_stats[removed_keyword]['total_length']
                    
                    logger.info(f"Removed keyword '{removed_keyword}', new total length: {total_length}")
                
                logger.info(f"Optimized keywords: {current_keywords}, total length: {total_length}")
                return current_keywords
            else:
                # Fallback to database query if no existing stats
                session = self.Session()
                try:
                    total_length = 0
                    
                    # Get initial message length
                    keyword_conditions = [MessageSearch.content.ilike(f'%{k}%') for k in current_keywords]
                    messages = session.query(TelegramMessage).join(
                        MessageSearch,
                        TelegramMessage.id == MessageSearch.message_id
                    ).filter(
                        and_(
                            TelegramMessage.chat_id == chat_id,
                            TelegramMessage.date >= start_date,
                            TelegramMessage.date <= end_date,
                            or_(*keyword_conditions)
                        )
                    ).all()
                    
                    total_length = sum(len(msg.text) for msg in messages)
                    
                    # Remove keywords from the end until we're under the limit
                    while total_length > max_length and len(current_keywords) > 1:
                        # Remove the last keyword
                        removed_keyword = current_keywords.pop()
                        
                        # Recalculate total length with remaining keywords
                        keyword_conditions = [MessageSearch.content.ilike(f'%{k}%') for k in current_keywords]
                        messages = session.query(TelegramMessage).join(
                            MessageSearch,
                            TelegramMessage.id == MessageSearch.message_id
                        ).filter(
                            and_(
                                TelegramMessage.chat_id == chat_id,
                                TelegramMessage.date >= start_date,
                                TelegramMessage.date <= end_date,
                                or_(*keyword_conditions)
                            )
                        ).all()
                        
                        total_length = sum(len(msg.text) for msg in messages)
                        
                        logger.info(f"Removed keyword '{removed_keyword}', new total length: {total_length}")
                    
                    logger.info(f"Optimized keywords: {current_keywords}, total length: {total_length}")
                    return current_keywords
                finally:
                    session.close()
            
        except Exception as e:
            logger.error(f"Error optimizing keywords: {str(e)}")
            return keywords  # Return original keywords if optimization fails
    
    def get_messages_with_context(
        self,
        chat_id: str,
        keywords: List[str],
        start_date: datetime,
        end_date: datetime,
        circ_count: int = 2,
        answer_depth_limit: int = 2,
        max_length: int = 10000
    ) -> Dict[str, Any]:
        """
        Retrieve messages with context based on keywords.
        
        Args:
            chat_id: ID of the chat to search in
            keywords: List of keywords to search for
            start_date: Start date for the search
            end_date: End date for the search
            circ_count: Number of messages to retrieve before and after keyword messages
            answer_depth_limit: Maximum depth of answer chains to follow
            max_length: Maximum total length of messages to retrieve
            
        Returns:
            Dictionary containing:
            - parameters used
            - keyword messages stats
            - context messages stats
            - answer chain stats
            - all retrieved messages
        """
        session = self.Session()
        try:
            # Prepare search conditions with keywords
            keyword_conditions = []
            for keyword in keywords:
                keyword_conditions.append(MessageSearch.content.ilike(f'%{keyword}%'))
            
            # Get messages containing keywords using the search index
            keyword_messages = session.query(TelegramMessage).join(
                MessageSearch,
                TelegramMessage.id == MessageSearch.message_id
            ).filter(
                and_(
                    TelegramMessage.chat_id == chat_id,
                    TelegramMessage.date >= start_date,
                    TelegramMessage.date <= end_date,
                    or_(*keyword_conditions)
                )
            ).order_by(TelegramMessage.date).all()
            
            # Get message IDs for context retrieval
            keyword_message_ids = [msg.message_id for msg in keyword_messages]
            
            # Get context messages (before and after)
            context_messages = []
            for msg_id in keyword_message_ids:
                # Get messages before
                before_messages = session.query(TelegramMessage).filter(
                    and_(
                        TelegramMessage.chat_id == chat_id,
                        TelegramMessage.message_id < msg_id
                    )
                ).order_by(TelegramMessage.message_id.desc()).limit(circ_count).all()
                
                # Get messages after
                after_messages = session.query(TelegramMessage).filter(
                    and_(
                        TelegramMessage.chat_id == chat_id,
                        TelegramMessage.message_id > msg_id
                    )
                ).order_by(TelegramMessage.message_id).limit(circ_count).all()
                
                context_messages.extend(before_messages + after_messages)
            
            # Get answer chains
            answer_chains = []
            for msg in keyword_messages:
                chain = self._get_answer_chain(session, msg, answer_depth_limit)
                answer_chains.extend(chain)
            
            # Calculate statistics
            stats = {
                'parameters': {
                    'chat_id': chat_id,
                    'keywords': keywords,  # Use original keywords
                    'date_range': f"{start_date} to {end_date}",
                    'circ_count': circ_count,
                    'answer_depth_limit': answer_depth_limit
                },
                'keyword_messages': {
                    'count': len(keyword_messages),
                    'total_length': sum(len(msg.text) for msg in keyword_messages),
                    'by_keyword': {
                        keyword: {
                            'count': len([msg for msg in keyword_messages if keyword.lower() in msg.text.lower()]),
                            'total_length': sum(len(msg.text) for msg in keyword_messages if keyword.lower() in msg.text.lower())
                        }
                        for keyword in keywords  # Use original keywords
                    }
                },
                'context_messages': {
                    'count': len(context_messages),
                    'total_length': sum(len(msg.text) for msg in context_messages)
                },
                'answer_chains': {
                    'count': len(answer_chains),
                    'total_length': sum(len(msg.text) for msg in answer_chains)
                }
            }
            
            # Combine all messages
            all_messages = list(set(keyword_messages + context_messages + answer_chains))
            all_messages.sort(key=lambda x: x.date)
            
            return {
                'stats': stats,
                'messages': [
                    {
                        'id': msg.id,
                        'message_id': msg.message_id,
                        'date': msg.date.isoformat(),
                        'text': msg.text,
                        'sender': msg.sender,
                        'chat_title': msg.chat_title,
                        'type': 'keyword' if msg in keyword_messages else
                               'context' if msg in context_messages else
                               'answer'
                    }
                    for msg in all_messages
                ]
            }
            
        finally:
            session.close()
    
    def _get_answer_chain(
        self,
        session,
        message: TelegramMessage,
        depth_limit: int,
        current_depth: int = 0,
        visited: Optional[set] = None
    ) -> List[TelegramMessage]:
        """Recursively get answer chain for a message."""
        if visited is None:
            visited = set()
        
        if current_depth >= depth_limit or message.id in visited:
            return []
        
        visited.add(message.id)
        chain = [message]
        
        # Get messages that are direct replies to this message
        answers = session.query(TelegramMessage).filter(
            and_(
                TelegramMessage.chat_id == message.chat_id,
                TelegramMessage.reply_to_message_id == message.message_id
            )
        ).order_by(TelegramMessage.date).all()
        
        # Follow each reply in the chain
        for answer in answers:
            chain.extend(self._get_answer_chain(session, answer, depth_limit, current_depth + 1, visited))
        
        return chain

    def get_messages_with_keywords(self, chat_id: str, keywords: List[str], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get messages containing keywords using the search index."""
        session = self.Session()
        try:
            # Prepare search conditions
            keyword_conditions = []
            for keyword in keywords:
                keyword_conditions.append(MessageSearch.content.ilike(f'%{keyword}%'))
            
            # Get messages containing keywords
            keyword_messages = session.query(TelegramMessage).join(
                MessageSearch,
                TelegramMessage.id == MessageSearch.message_id
            ).filter(
                and_(
                    TelegramMessage.chat_id == chat_id,
                    TelegramMessage.date >= start_date,
                    TelegramMessage.date <= end_date,
                    or_(*keyword_conditions)
                )
            ).order_by(TelegramMessage.date).all()
            
            return [{
                'id': msg.id,
                'chat_id': msg.chat_id,
                'message_id': msg.message_id,
                'date': msg.date,
                'text': msg.text,
                'sender': msg.sender,
                'chat_title': msg.chat_title,
                'reply_to_message_id': msg.reply_to_message_id
            } for msg in keyword_messages]
            
        except Exception as e:
            logger.error(f"Error retrieving messages with keywords: {str(e)}")
            return []
        finally:
            session.close() 