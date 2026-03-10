# schemas.py - Explicit schemas over ad-hoc objects
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

class InstructionType(Enum):
    TRANSACTION = "vdt"
    PAIR_CREATION = "Create"

@dataclass
class ProcessingContext:
    """Explicit state container - no hidden threading of IDs"""
    log_id: Optional[str] = None
    meta_id: Optional[str] = None
    pair_id: Optional[str] = None
    
    def update(self, **kwargs) -> 'ProcessingContext':
        """Immutable updates"""
        return ProcessingContext(
            log_id=kwargs.get('log_id', self.log_id),
            meta_id=kwargs.get('meta_id', self.meta_id),
            pair_id=kwargs.get('pair_id', self.pair_id)
        )

@dataclass
class DecodedInstruction:
    data: Dict[str, Any]
    mint: str
    user_address: Optional[str]
    bonding_curve: Optional[str]
    type: InstructionType

@dataclass
class TransactionData:
    signature: str
    signatures: List[str]
    slot: int
    program_id: str
    log_id: Optional[str]
    logs: List[Any]
    tcns: List[Dict[str, Any]]
    context: ProcessingContext

# registries.py - Registries over globals
class InstructionHandlerRegistry:
    """Registry pattern for instruction processors"""
    
    def __init__(self):
        self._handlers: Dict[InstructionType, callable] = {}
    
    def register(self, instruction_type: InstructionType):
        def decorator(func):
            self._handlers[instruction_type] = func
            return func
        return decorator
    
    def get_handler(self, instruction_type: InstructionType):
        return self._handlers.get(instruction_type)

# Create registry instance
instruction_registry = InstructionHandlerRegistry()

# processors.py - Explicit environment wiring
class TransactionProcessor:
    """Explicit dependencies, no smart defaults"""
    
    def __init__(
        self,
        decoder_service,
        pair_service,
        metadata_service,
        queue_service,
        log_repo,
        transaction_repo,
        program_id: str,  # explicit, not defaulted
        decimals: int = 6
    ):
        self.decoder = decoder_service
        self.pairs = pair_service
        self.metadata = metadata_service
        self.queues = queue_service
        self.log_repo = log_repo
        self.tx_repo = transaction_repo
        self.program_id = program_id
        self.decimals = decimals
    
    async def decode_instruction(
        self,
        data_str: str,
        signature: str,
        invocation_index: int
    ) -> Optional[DecodedInstruction]:
        """Single responsibility: decode instruction data"""
        try:
            decoded = await self.decoder.decode_program_data_unified(
                program_id=self.program_id,
                data=data_str,
                context="instruction"
            )
            
            if not decoded or not decoded.get('data'):
                return None
            
            data = decoded['data']
            
            # Determine instruction type
            if data_str.startswith('vdt'):
                instr_type = InstructionType.TRANSACTION
            else:
                instr_type = InstructionType.PAIR_CREATION
            
            return DecodedInstruction(
                data=data,
                mint=data.get('mint'),
                user_address=data.get('user_address'),
                bonding_curve=data.get('bonding_curve'),
                type=instr_type
            )
        except Exception as e:
            print(f"Decode failed for {signature}: {e}")
            return None
    
    async def ensure_metadata(
        self,
        mint: str,
        decoded_data: Dict[str, Any],
        current_meta_id: Optional[str]
    ) -> Optional[str]:
        """Single point of metadata resolution"""
        if current_meta_id:
            return current_meta_id
        
        metadata = await self.metadata.fetch_or_create(
            mint=mint,
            decoded_data=decoded_data,
            decimals=self.decimals
        )
        return metadata.get('id') if metadata else None
    
    async def ensure_pair(
        self,
        mint: str,
        signature: str,
        context: ProcessingContext,
        user_address: Optional[str] = None,
        bonding_curve: Optional[str] = None
    ) -> Optional[str]:
        """Single point of pair resolution - eliminates redundant lookups"""
        if context.pair_id:
            return context.pair_id
        
        # Single upsert call handles both get and create
        pair_data = {
            'signature': signature,
            'program_id': self.program_id,
            'mint': mint,
            'user_address': user_address,
            'meta_id': context.meta_id,
            'log_id': context.log_id,
            'bonding_curve': bonding_curve
        }
        
        return await self.pairs.upsert(pair_data)
    
    async def enqueue_follow_up_tasks(
        self,
        instruction: DecodedInstruction,
        context: ProcessingContext
    ):
        """Queues over callbacks - batch queue operations"""
        if not context.pair_id:
            return
        
        tasks = []
        
        if instruction.type == InstructionType.PAIR_CREATION:
            tasks.extend([
                {'queue': 'signatures', 'payload': {
                    'address': instruction.user_address,
                    'until': None,
                    'limit': 1000
                }},
                {'queue': 'metadata', 'payload': {
                    'mint': instruction.mint
                }}
            ])
        elif instruction.type == InstructionType.TRANSACTION:
            tasks.extend([
                {'queue': 'transactions', 'payload': {
                    'mint': instruction.mint,
                    'pair_id': context.pair_id,
                    'program_id': self.program_id
                }},
                {'queue': 'metadata', 'payload': {
                    'mint': instruction.mint
                }}
            ])
        
        # Batch send to reduce overhead
        await self.queues.send_batch(tasks)
    
    @instruction_registry.register(InstructionType.PAIR_CREATION)
    async def process_pair_creation(
        self,
        instruction: DecodedInstruction,
        signature: str,
        txn_data: TransactionData
    ) -> ProcessingContext:
        """Process pair creation instruction"""
        context = txn_data.context
        
        # Resolve dependencies in order
        meta_id = await self.ensure_metadata(
            instruction.mint,
            instruction.data,
            context.meta_id
        )
        
        context = context.update(meta_id=meta_id)
        
        pair_id = await self.ensure_pair(
            mint=instruction.mint,
            signature=signature,
            context=context,
            user_address=instruction.user_address,
            bonding_curve=instruction.bonding_curve
        )
        
        context = context.update(pair_id=pair_id)
        
        # Queue follow-up work
        await self.enqueue_follow_up_tasks(instruction, context)
        
        return context
    
    @instruction_registry.register(InstructionType.TRANSACTION)
    async def process_transaction_instruction(
        self,
        instruction: DecodedInstruction,
        signature: str,
        txn_data: TransactionData
    ) -> ProcessingContext:
        """Process transaction instruction"""
        context = txn_data.context
        
        # Add TCN data
        tcn_data = await self.decoder.decode_transaction_data(
            instruction.data,
            self.decimals,
            invocation=txn_data.logs.index(instruction)
        )
        txn_data.tcns.append(tcn_data)
        
        # Resolve dependencies
        meta_id = await self.ensure_metadata(
            instruction.mint,
            instruction.data,
            context.meta_id
        )
        
        context = context.update(meta_id=meta_id)
        
        pair_id = await self.ensure_pair(
            mint=instruction.mint,
            signature=signature,
            context=context,
            user_address=instruction.user_address,
            bonding_curve=instruction.bonding_curve
        )
        
        context = context.update(pair_id=pair_id)
        
        # Queue follow-up work
        await self.enqueue_follow_up_tasks(instruction, context)
        
        return context
    
    async def process_transaction(
        self,
        txn_msg: Dict[str, Any]
    ) -> Optional[TransactionData]:
        """Main orchestration - clear linear flow"""
        signature = txn_msg.get('signature')
        if not signature:
            print("Missing signature")
            return None
        
        # Check if already processed (idempotency)
        log_data = await self.log_repo.fetch_by_signature(signature)
        if log_data and log_data.get('sorted'):
            return await self.tx_repo.fetch_by_signature(signature)
        
        # Parse input
        logs = txn_msg.get('parsed_logs')
        if not logs:
            print(f"No logs for {signature}")
            return None
        
        # Initialize transaction data
        txn_data = TransactionData(
            signature=signature,
            signatures=txn_msg.get('signatures', []),
            slot=txn_msg.get('slot'),
            program_id=self.program_id,
            log_id=txn_msg.get('id'),
            logs=self._flatten_invocations(logs),
            tcns=[],
            context=ProcessingContext(log_id=txn_msg.get('id'))
        )
        
        # Process each instruction
        for invocation in txn_data.logs:
            data_str = self._extract_data_string(invocation)
            if not data_str:
                continue
            
            # Decode instruction
            instruction = await self.decode_instruction(
                data_str,
                signature,
                invocation.get('invocation_index')
            )
            
            if not instruction:
                continue
            
            # Get handler from registry
            handler = instruction_registry.get_handler(instruction.type)
            if not handler:
                continue
            
            # Process instruction and update context
            txn_data.context = await handler(
                self,
                instruction,
                signature,
                txn_data
            )
        
        # Persist results if we processed anything
        if txn_data.tcns:
            await self.tx_repo.upsert(txn_data)
            await self.log_repo.mark_processed(signature)
        
        return txn_data
    
    def _flatten_invocations(self, invocations: List) -> List:
        """Helper to flatten nested invocations"""
        result = []
        for inv in invocations:
            result.append(inv)
            if inv.get('children'):
                result.extend(self._flatten_invocations(inv['children']))
        return result
    
    def _extract_data_string(self, invocation: Dict) -> Optional[str]:
        """Helper to extract data string"""
        data = invocation.get('data')
        if not data:
            return None
        return str(data).strip() if data else None


# main.py - Explicit wiring
async def create_processor(config):
    """Factory with explicit dependencies"""
    return TransactionProcessor(
        decoder_service=DecoderService(config.rpc_url),
        pair_service=PairService(config.db),
        metadata_service=MetadataService(config.db, config.ipfs_gateway),
        queue_service=QueueService(config.rabbit_url),
        log_repo=LogRepository(config.db),
        transaction_repo=TransactionRepository(config.db),
        program_id=config.program_id,  # explicit, not magic
        decimals=config.decimals
    )

# Usage
async def main():
    config = load_config()  # from environment/file, not defaults
    processor = await create_processor(config)
    
    txn_msg = await get_next_message()
    result = await processor.process_transaction(txn_msg)
main()
