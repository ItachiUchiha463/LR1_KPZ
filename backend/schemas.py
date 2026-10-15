from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
VALID_OPS = {'<', '<=', '>', '>=', '==', '!=', 'in', 'not_in', 'is_true', 'is_false', 'contains'}

class Condition(BaseModel):
    fact: str = Field(..., min_length=1, description='Назва факту з опису фактів')
    op: str = Field('==', description='Оператор порівняння')
    value: Optional[Any] = Field(None, description='Порогове значення (константа)')
    ref_fact: Optional[str] = Field(None, description='Порівняння з іншим фактом')
    factor: Optional[float] = Field(None, description='Множник для ref_fact')

    @field_validator('op')
    @classmethod
    def check_op(cls, v: str) -> str:
        if v not in VALID_OPS:
            raise ValueError(f"Невідомий оператор '{v}'. Дозволені: {sorted(VALID_OPS)}")
        return v

    @field_validator('factor')
    @classmethod
    def check_factor(cls, v):
        if v is not None and v == 0:
            raise ValueError('factor не може бути 0 - умова стане безглуздою')
        return v

class Conclusion(BaseModel):
    fact: str = Field(..., min_length=1)
    value: Any

class RuleBase(BaseModel):
    id: str = Field(..., min_length=1, description='Людський ідентифікатор, напр. Пр-01')
    branch: str = Field(..., min_length=1, description='Гілка: RAM, CPU, Диск, ...')
    layer: int = Field(1, ge=1, le=10, description='Шар виводу')
    conditions: List[Condition] = Field(..., min_length=1, description="Умови, з'єднані через І")
    conclusions: List[Conclusion] = Field(..., min_length=1)
    text: str = Field('', description='Читабельний запис ЯКЩО-ТО для звіту й редактора')
    note: str = ''
    enabled: bool = True
    rule_type: Literal['intermediate', 'diagnostic'] = Field('intermediate', description="intermediate - виводить проміжний стан; diagnostic - ставить діагноз (conclusions матиме рівно один запис {fact: 'діагноз', value: код_з_довідника_diagnoses})")
    cf: float = Field(1.0, ge=0.0, le=1.0, description='Впевненість правила (0-1). Для діагностичних правил кілька незалежних підтверджень того самого коду комбінуються формулою MYCIN.')

    @field_validator('cf')
    @classmethod
    def check_cf_bounds(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('cf має бути в межах 0.0-1.0')
        return v

class RuleOut(RuleBase):
    mongo_id: str = Field(..., alias='_id')
    model_config = {'populate_by_name': True}

class FactSpec(BaseModel):
    name: str = Field(..., min_length=1)
    kind: Literal['raw', 'derived', 'neural']
    type: Optional[str] = None
    aggregation: Optional[Literal['single', 'collect', 'max']] = None
    unit: Optional[str] = None
    values: Optional[List[str]] = None
    note: Optional[str] = None
    default: Optional[Any] = Field(None, description='Значення, яке факт отримує ДО старту виводу, якщо жодне правило його не встановить (лише для derived)')

class FactOut(FactSpec):
    mongo_id: str = Field(..., alias='_id')
    model_config = {'populate_by_name': True}

class DiagnosisSpec(BaseModel):
    code: str = Field(..., min_length=1, description='Технічний код, напр. memory_leak_critical')
    name: str = Field(..., min_length=1, description='Людська назва для оператора')
    criticality: int = Field(..., ge=1, le=4, description='1 (найнижча) - 4 (найвища)')
    description: str = Field('', description='Що означає цей діагноз')
    recommendation: str = Field('', description='Що робити оператору')

class DiagnosisOut(DiagnosisSpec):
    mongo_id: str = Field(..., alias='_id')
    model_config = {'populate_by_name': True}

class DiagnoseRequest(BaseModel):
    facts: Dict[str, Any] = Field(..., description='Вхідні показники моніторингу')
    include_trace: bool = Field(True, description='Повертати детальне трасування')
    save_run: bool = Field(False, description='Зберегти прогін у колекцію runs')
    label: str = Field('', description='Підпис прогону (напр. назва сценарію)')

class DiagnoseResponse(BaseModel):
    run_id: Optional[str] = None
    facts: Dict[str, Any]
    diagnoses: List[str]
    diagnoses_detail: List[Dict[str, Any]] = Field(default_factory=list, description='Повна форма: назва, критичність, CF, рівень (проблема/можлива), рекомендація - для інтерфейсу')
    severity: Optional[str] = None
    problem_criticality: Optional[Any] = None
    fired_rules: List[Dict[str, Any]]
    trace: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    iterations: int
    missing_raw_facts: List[str]
    unknown_input_facts: List[str]

class RunSummary(BaseModel):
    mongo_id: str = Field(..., alias='_id')
    label: str
    created_at: str
    diagnoses: List[str]
    diagnoses_detail: List[Dict[str, Any]] = Field(default_factory=list)
    severity: Optional[str] = None
    has_conflicts: bool
    model_config = {'populate_by_name': True}

class RunDetail(DiagnoseResponse):
    label: str = ''
    created_at: str = ''

class HealthOut(BaseModel):
    api: bool = True
    mongo_connected: bool
    mongo_message: str
    rules_in_db: Optional[int] = None

class StatsOut(BaseModel):
    rule_count: int
    fact_count: int
    branches: List[str]
    rules_per_branch: Dict[str, int]
    rules_per_layer: Dict[str, int]
    disabled_rules: int
