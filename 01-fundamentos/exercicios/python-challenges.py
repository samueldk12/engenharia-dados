"""
============================================================================
EXERCÍCIOS: Python para Engenharia de Dados
Nível: Intermediário-Avançado
Objetivo: Dominar pandas, async, type hints, otimização
============================================================================
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time
from functools import wraps


# ============================================================================
# EXERCÍCIO 1: Pandas Advanced Operations
# ============================================================================

def ex01_sales_analysis():
    """
    Crie um DataFrame de vendas e calcule:
    1. Top 3 produtos por categoria
    2. Running total de vendas por dia
    3. Moving average de 7 dias
    4. Percentual de cada produto na categoria
    """

    # Setup: Criar dados de exemplo
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')

    data = {
        'date': np.repeat(dates, 5),
        'product': np.random.choice(['A', 'B', 'C', 'D', 'E'], size=len(dates) * 5),
        'category': np.random.choice(['Electronics', 'Clothing', 'Books'], size=len(dates) * 5),
        'revenue': np.random.uniform(100, 1000, size=len(dates) * 5),
        'quantity': np.random.randint(1, 20, size=len(dates) * 5)
    }

    df = pd.DataFrame(data)

    # TODO: Implementar sua solução
    # 1. Top 3 produtos por categoria

    # 2. Running total de vendas por dia

    # 3. Moving average de 7 dias

    # 4. Percentual de cada produto na categoria

    pass  # Remova isso e implemente


# SOLUÇÃO:
def ex01_sales_analysis_solution():
    """Solução completa do exercício 1"""

    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')

    data = {
        'date': np.repeat(dates, 5),
        'product': np.random.choice(['A', 'B', 'C', 'D', 'E'], size=len(dates) * 5),
        'category': np.random.choice(['Electronics', 'Clothing', 'Books'], size=len(dates) * 5),
        'revenue': np.random.uniform(100, 1000, size=len(dates) * 5),
        'quantity': np.random.randint(1, 20, size=len(dates) * 5)
    }

    df = pd.DataFrame(data)

    # 1. Top 3 produtos por categoria
    top_products = (
        df.groupby(['category', 'product'])
        .agg({'revenue': 'sum'})
        .reset_index()
        .assign(rank=lambda x: x.groupby('category')['revenue'].rank(method='dense', ascending=False))
        .query('rank <= 3')
        .sort_values(['category', 'rank'])
    )

    print("Top 3 produtos por categoria:")
    print(top_products)

    # 2. Running total de vendas por dia
    daily_sales = (
        df.groupby('date')
        .agg({'revenue': 'sum'})
        .reset_index()
        .assign(running_total=lambda x: x['revenue'].cumsum())
    )

    print("\nRunning total de vendas:")
    print(daily_sales.head(10))

    # 3. Moving average de 7 dias
    daily_sales['moving_avg_7d'] = daily_sales['revenue'].rolling(window=7).mean()

    print("\nMoving average 7 dias:")
    print(daily_sales[['date', 'revenue', 'moving_avg_7d']].tail(10))

    # 4. Percentual de cada produto na categoria
    category_product_pct = (
        df.groupby(['category', 'product'])
        .agg({'revenue': 'sum'})
        .reset_index()
        .assign(
            category_total=lambda x: x.groupby('category')['revenue'].transform('sum'),
            pct_of_category=lambda x: (x['revenue'] / x['category_total'] * 100).round(2)
        )
    )

    print("\nPercentual por categoria:")
    print(category_product_pct)

    return df, top_products, daily_sales, category_product_pct


# ============================================================================
# EXERCÍCIO 2: Memory Optimization
# ============================================================================

def ex02_optimize_memory():
    """
    Otimize o uso de memória de um DataFrame grande
    1. Use tipos de dados apropriados (category, int32, etc)
    2. Compare uso de memória antes e depois
    3. Implemente chunked processing
    """

    # Setup: Criar DataFrame grande
    n_rows = 1_000_000

    df = pd.DataFrame({
        'id': range(n_rows),
        'category': np.random.choice(['A', 'B', 'C', 'D', 'E'], n_rows),
        'country': np.random.choice(['USA', 'Brazil', 'UK', 'Germany'], n_rows),
        'value': np.random.randn(n_rows),
        'quantity': np.random.randint(1, 100, n_rows),
        'date': pd.date_range('2020-01-01', periods=n_rows, freq='1min')
    })

    print(f"Memória original: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

    # TODO: Otimize o DataFrame
    # Dicas:
    # - category para strings repetitivas
    # - int32/int16 para inteiros pequenos
    # - float32 se precisão não é crítica

    pass


# SOLUÇÃO:
def ex02_optimize_memory_solution():
    """Solução de otimização de memória"""

    n_rows = 1_000_000

    # DataFrame original
    df_original = pd.DataFrame({
        'id': range(n_rows),
        'category': np.random.choice(['A', 'B', 'C', 'D', 'E'], n_rows),
        'country': np.random.choice(['USA', 'Brazil', 'UK', 'Germany'], n_rows),
        'value': np.random.randn(n_rows),
        'quantity': np.random.randint(1, 100, n_rows),
        'date': pd.date_range('2020-01-01', periods=n_rows, freq='1min')
    })

    memory_before = df_original.memory_usage(deep=True).sum() / 1024**2
    print(f"Memória ANTES: {memory_before:.2f} MB")
    print(df_original.dtypes)

    # DataFrame otimizado
    df_optimized = df_original.copy()
    df_optimized['id'] = df_optimized['id'].astype('int32')
    df_optimized['category'] = df_optimized['category'].astype('category')
    df_optimized['country'] = df_optimized['country'].astype('category')
    df_optimized['value'] = df_optimized['value'].astype('float32')
    df_optimized['quantity'] = df_optimized['quantity'].astype('int8')  # 1-100 cabe em int8

    memory_after = df_optimized.memory_usage(deep=True).sum() / 1024**2
    print(f"\nMemória DEPOIS: {memory_after:.2f} MB")
    print(f"Redução: {(1 - memory_after/memory_before) * 100:.2f}%")
    print(df_optimized.dtypes)

    return df_original, df_optimized


# ============================================================================
# EXERCÍCIO 3: Async I/O para Data Engineering
# ============================================================================

async def ex03_async_api_fetch():
    """
    Implemente fetching assíncrono de múltiplas APIs
    1. Fetch dados de 10 URLs em paralelo
    2. Handle erros e retries
    3. Combine os resultados em um DataFrame
    """

    urls = [
        f"https://jsonplaceholder.typicode.com/posts/{i}"
        for i in range(1, 11)
    ]

    # TODO: Implementar async fetch
    # Dicas:
    # - Use aiohttp.ClientSession
    # - asyncio.gather para paralelismo
    # - try/except para error handling

    pass


# SOLUÇÃO:
async def fetch_url(session: aiohttp.ClientSession, url: str, retries: int = 3) -> Dict:
    """Fetch URL com retry logic"""
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Status {response.status} para {url}")
        except Exception as e:
            print(f"Tentativa {attempt + 1} falhou para {url}: {e}")
            if attempt == retries - 1:
                return None
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    return None


async def ex03_async_api_fetch_solution():
    """Solução de async API fetching"""

    urls = [
        f"https://jsonplaceholder.typicode.com/posts/{i}"
        for i in range(1, 11)
    ]

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks)

    # Filtrar None (falhas)
    valid_results = [r for r in results if r is not None]

    # Converter para DataFrame
    df = pd.DataFrame(valid_results)
    print(f"\nFetch concluído: {len(valid_results)} de {len(urls)} sucessos")
    print(df.head())

    return df


# ============================================================================
# EXERCÍCIO 4: Data Pipeline com Classes
# ============================================================================

@dataclass
class PipelineConfig:
    """Configuração do pipeline"""
    source_path: str
    destination_path: str
    chunk_size: int = 10000
    date_columns: List[str] = None
    numeric_columns: List[str] = None


class DataPipeline:
    """
    Pipeline de dados com:
    1. Extração (CSV, JSON, API)
    2. Validação
    3. Transformação
    4. Carregamento
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.data: Optional[pd.DataFrame] = None
        self.errors: List[str] = []

    def extract(self) -> 'DataPipeline':
        """TODO: Implementar extração de dados"""
        pass

    def validate(self) -> 'DataPipeline':
        """TODO: Implementar validações"""
        pass

    def transform(self) -> 'DataPipeline':
        """TODO: Implementar transformações"""
        pass

    def load(self) -> 'DataPipeline':
        """TODO: Implementar carregamento"""
        pass

    def run(self):
        """Executar pipeline completo"""
        return (
            self.extract()
            .validate()
            .transform()
            .load()
        )


# SOLUÇÃO:
class DataPipelineSolution:
    """Pipeline completo com implementação"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.data: Optional[pd.DataFrame] = None
        self.errors: List[str] = []
        self.metrics: Dict = {
            'rows_read': 0,
            'rows_valid': 0,
            'rows_written': 0,
            'errors': 0
        }

    def extract(self) -> 'DataPipelineSolution':
        """Extrai dados da fonte"""
        try:
            if self.config.source_path.endswith('.csv'):
                self.data = pd.read_csv(
                    self.config.source_path,
                    parse_dates=self.config.date_columns,
                    chunksize=None
                )
            elif self.config.source_path.endswith('.json'):
                self.data = pd.read_json(self.config.source_path)

            self.metrics['rows_read'] = len(self.data)
            print(f" Extraídos {len(self.data)} registros")

        except Exception as e:
            self.errors.append(f"Erro na extração: {e}")
            print(f" Erro na extração: {e}")

        return self

    def validate(self) -> 'DataPipelineSolution':
        """Valida qualidade dos dados"""
        if self.data is None:
            return self

        initial_count = len(self.data)

        # 1. Remove duplicatas
        self.data = self.data.drop_duplicates()

        # 2. Remove linhas com nulls em colunas críticas
        if self.config.numeric_columns:
            self.data = self.data.dropna(subset=self.config.numeric_columns)

        # 3. Valida tipos de dados
        for col in self.config.numeric_columns or []:
            if col in self.data.columns:
                self.data[col] = pd.to_numeric(self.data[col], errors='coerce')

        self.data = self.data.dropna()

        removed = initial_count - len(self.data)
        self.metrics['rows_valid'] = len(self.data)
        self.metrics['errors'] = removed

        print(f" Validação: {removed} registros removidos, {len(self.data)} válidos")

        return self

    def transform(self) -> 'DataPipelineSolution':
        """Aplica transformações"""
        if self.data is None:
            return self

        # Exemplo: adicionar colunas derivadas
        if 'date' in self.data.columns:
            self.data['year'] = pd.to_datetime(self.data['date']).dt.year
            self.data['month'] = pd.to_datetime(self.data['date']).dt.month
            self.data['day_of_week'] = pd.to_datetime(self.data['date']).dt.dayofweek

        print(f" Transformações aplicadas")

        return self

    def load(self) -> 'DataPipelineSolution':
        """Carrega dados no destino"""
        if self.data is None:
            return self

        try:
            if self.config.destination_path.endswith('.csv'):
                self.data.to_csv(self.config.destination_path, index=False)
            elif self.config.destination_path.endswith('.parquet'):
                self.data.to_parquet(self.config.destination_path, index=False)

            self.metrics['rows_written'] = len(self.data)
            print(f" {len(self.data)} registros carregados em {self.config.destination_path}")

        except Exception as e:
            self.errors.append(f"Erro no carregamento: {e}")
            print(f" Erro no carregamento: {e}")

        return self

    def run(self):
        """Executa pipeline completo"""
        print("=" * 60)
        print("INICIANDO PIPELINE")
        print("=" * 60)

        start_time = time.time()

        self.extract().validate().transform().load()

        execution_time = time.time() - start_time

        print("=" * 60)
        print("PIPELINE CONCLUÍDO")
        print(f"Tempo de execução: {execution_time:.2f}s")
        print(f"Métricas: {self.metrics}")
        if self.errors:
            print(f"Erros: {self.errors}")
        print("=" * 60)

        return self


# ============================================================================
# EXERCÍCIO 5: Performance - Vetorização vs Loops
# ============================================================================

def ex05_performance_comparison():
    """
    Compare performance de diferentes abordagens:
    1. Loop with iterrows (mais lento)
    2. Loop with itertuples (rápido)
    3. apply() (médio)
    4. Vetorização (mais rápido)
    """

    df = pd.DataFrame({
        'a': np.random.randint(1, 100, 100000),
        'b': np.random.randint(1, 100, 100000)
    })

    def calculate_complex(a, b):
        """Função complexa para calcular"""
        return (a ** 2 + b ** 2) ** 0.5 * np.log(a + b + 1)

    # TODO: Implemente as 4 abordagens e compare os tempos

    pass


# SOLUÇÃO:
def ex05_performance_comparison_solution():
    """Comparação de performance"""

    df = pd.DataFrame({
        'a': np.random.randint(1, 100, 100000),
        'b': np.random.randint(1, 100, 100000)
    })

    def calculate_complex(a, b):
        return (a ** 2 + b ** 2) ** 0.5 * np.log(a + b + 1)

    # 1. iterrows (MUITO LENTO - NÃO USE)
    start = time.time()
    results = []
    for idx, row in df.iterrows():
        results.append(calculate_complex(row['a'], row['b']))
    df['result_iterrows'] = results
    time_iterrows = time.time() - start
    print(f"iterrows: {time_iterrows:.4f}s")

    # 2. itertuples (LENTO)
    start = time.time()
    results = []
    for row in df.itertuples():
        results.append(calculate_complex(row.a, row.b))
    df['result_itertuples'] = results
    time_itertuples = time.time() - start
    print(f"itertuples: {time_itertuples:.4f}s (speedup: {time_iterrows/time_itertuples:.2f}x)")

    # 3. apply (MÉDIO)
    start = time.time()
    df['result_apply'] = df.apply(lambda row: calculate_complex(row['a'], row['b']), axis=1)
    time_apply = time.time() - start
    print(f"apply: {time_apply:.4f}s (speedup: {time_iterrows/time_apply:.2f}x)")

    # 4. Vetorização (RÁPIDO!)
    start = time.time()
    df['result_vectorized'] = calculate_complex(df['a'].values, df['b'].values)
    time_vectorized = time.time() - start
    print(f"vetorização: {time_vectorized:.4f}s (speedup: {time_iterrows/time_vectorized:.2f}x)")

    print(f"\nVetorização é {time_iterrows/time_vectorized:.0f}x mais rápido que iterrows!")

    return df


# ============================================================================
# EXERCÍCIO 6: Parallel Processing
# ============================================================================

def process_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Processa um chunk de dados (função pesada)"""
    time.sleep(0.1)  # Simula processamento pesado
    chunk['processed'] = chunk['value'] * 2 + chunk['value'].mean()
    return chunk


def ex06_parallel_processing():
    """
    Implemente processamento paralelo de DataFrame grande
    1. Split em chunks
    2. Process em paralelo (ThreadPoolExecutor ou ProcessPoolExecutor)
    3. Combine resultados
    """

    # TODO: Implementar processamento paralelo

    pass


# SOLUÇÃO:
def ex06_parallel_processing_solution():
    """Processamento paralelo de DataFrame"""

    # Criar DataFrame grande
    n_rows = 100000
    df = pd.DataFrame({
        'id': range(n_rows),
        'value': np.random.randn(n_rows)
    })

    # 1. Processamento sequencial
    print("Processamento SEQUENCIAL:")
    start = time.time()
    chunks = np.array_split(df, 10)
    results_seq = [process_chunk(chunk) for chunk in chunks]
    df_result_seq = pd.concat(results_seq)
    time_seq = time.time() - start
    print(f"Tempo: {time_seq:.2f}s")

    # 2. Processamento paralelo com ThreadPoolExecutor
    print("\nProcessamento PARALELO (Threads):")
    start = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        results_parallel = list(executor.map(process_chunk, chunks))
    df_result_parallel = pd.concat(results_parallel)
    time_parallel = time.time() - start
    print(f"Tempo: {time_parallel:.2f}s")
    print(f"Speedup: {time_seq/time_parallel:.2f}x")

    # 3. ProcessPoolExecutor para CPU-bound tasks
    print("\nProcessamento PARALELO (Processes):")
    start = time.time()
    with ProcessPoolExecutor(max_workers=4) as executor:
        results_process = list(executor.map(process_chunk, chunks))
    df_result_process = pd.concat(results_process)
    time_process = time.time() - start
    print(f"Tempo: {time_process:.2f}s")
    print(f"Speedup: {time_seq/time_process:.2f}x")

    return df_result_seq, df_result_parallel, df_result_process


# ============================================================================
# EXERCÍCIO 7: Data Quality Checks
# ============================================================================

@dataclass
class DataQualityResult:
    """Resultado de validação de qualidade"""
    passed: bool
    check_name: str
    message: str
    details: Dict


class DataQualityChecker:
    """
    Implementar checks de qualidade de dados:
    1. Completeness (% de nulls)
    2. Uniqueness (duplicatas)
    3. Validity (valores dentro de ranges)
    4. Consistency (relações entre colunas)
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.results: List[DataQualityResult] = []

    def check_completeness(self, column: str, threshold: float = 0.95) -> DataQualityResult:
        """TODO: Verificar completeness"""
        pass

    def check_uniqueness(self, column: str) -> DataQualityResult:
        """TODO: Verificar unicidade"""
        pass

    def check_validity(self, column: str, min_val: float, max_val: float) -> DataQualityResult:
        """TODO: Verificar valores válidos"""
        pass

    def run_all_checks(self) -> List[DataQualityResult]:
        """TODO: Executar todos os checks"""
        pass


# SOLUÇÃO:
class DataQualityCheckerSolution:
    """Implementação completa de data quality checks"""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.results: List[DataQualityResult] = []

    def check_completeness(self, column: str, threshold: float = 0.95) -> DataQualityResult:
        """Verifica se coluna tem dados suficientes"""
        non_null_pct = self.df[column].notna().sum() / len(self.df)
        passed = non_null_pct >= threshold

        result = DataQualityResult(
            passed=passed,
            check_name="Completeness",
            message=f"Column '{column}' is {non_null_pct*100:.2f}% complete",
            details={
                'column': column,
                'non_null_pct': non_null_pct,
                'threshold': threshold,
                'null_count': self.df[column].isna().sum()
            }
        )

        self.results.append(result)
        return result

    def check_uniqueness(self, column: str) -> DataQualityResult:
        """Verifica duplicatas"""
        duplicates = self.df[column].duplicated().sum()
        passed = duplicates == 0

        result = DataQualityResult(
            passed=passed,
            check_name="Uniqueness",
            message=f"Column '{column}' has {duplicates} duplicates",
            details={
                'column': column,
                'duplicates': duplicates,
                'unique_count': self.df[column].nunique(),
                'total_count': len(self.df)
            }
        )

        self.results.append(result)
        return result

    def check_validity(self, column: str, min_val: float, max_val: float) -> DataQualityResult:
        """Verifica se valores estão no range esperado"""
        invalid = ((self.df[column] < min_val) | (self.df[column] > max_val)).sum()
        passed = invalid == 0

        result = DataQualityResult(
            passed=passed,
            check_name="Validity",
            message=f"Column '{column}' has {invalid} invalid values",
            details={
                'column': column,
                'invalid_count': invalid,
                'min_val': min_val,
                'max_val': max_val,
                'actual_min': self.df[column].min(),
                'actual_max': self.df[column].max()
            }
        )

        self.results.append(result)
        return result

    def check_consistency(self, col1: str, col2: str, condition: str) -> DataQualityResult:
        """Verifica consistência entre colunas"""
        if condition == "col1 <= col2":
            invalid = (self.df[col1] > self.df[col2]).sum()
        elif condition == "col1 < col2":
            invalid = (self.df[col1] >= self.df[col2]).sum()
        else:
            invalid = 0

        passed = invalid == 0

        result = DataQualityResult(
            passed=passed,
            check_name="Consistency",
            message=f"Columns '{col1}' and '{col2}' have {invalid} inconsistent rows",
            details={
                'col1': col1,
                'col2': col2,
                'condition': condition,
                'invalid_count': invalid
            }
        )

        self.results.append(result)
        return result

    def run_all_checks(self) -> List[DataQualityResult]:
        """Executa todos os checks configurados"""
        print("=" * 60)
        print("EXECUTANDO DATA QUALITY CHECKS")
        print("=" * 60)

        for result in self.results:
            status = " PASS" if result.passed else " FAIL"
            print(f"{status} | {result.check_name}: {result.message}")

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        print("=" * 60)
        print(f"RESULTADO: {passed}/{total} checks passaram")
        print("=" * 60)

        return self.results


# ============================================================================
# TESTE DOS EXERCÍCIOS
# ============================================================================

def run_all_exercises():
    """Executa todos os exercícios"""

    print("\n" + "=" * 80)
    print("EXERCÍCIO 1: Pandas Advanced Operations")
    print("=" * 80)
    ex01_sales_analysis_solution()

    print("\n" + "=" * 80)
    print("EXERCÍCIO 2: Memory Optimization")
    print("=" * 80)
    ex02_optimize_memory_solution()

    print("\n" + "=" * 80)
    print("EXERCÍCIO 3: Async API Fetch")
    print("=" * 80)
    # asyncio.run(ex03_async_api_fetch_solution())

    print("\n" + "=" * 80)
    print("EXERCÍCIO 5: Performance Comparison")
    print("=" * 80)
    ex05_performance_comparison_solution()

    print("\n" + "=" * 80)
    print("EXERCÍCIO 6: Parallel Processing")
    print("=" * 80)
    ex06_parallel_processing_solution()

    print("\n" + "=" * 80)
    print("EXERCÍCIO 7: Data Quality Checks - EXEMPLO")
    print("=" * 80)

    # Exemplo de uso do DataQualityChecker
    test_df = pd.DataFrame({
        'user_id': range(100),
        'age': np.random.randint(18, 80, 100),
        'revenue': np.random.uniform(0, 1000, 100),
        'cost': np.random.uniform(0, 500, 100)
    })

    checker = DataQualityCheckerSolution(test_df)
    checker.check_completeness('user_id', threshold=0.95)
    checker.check_uniqueness('user_id')
    checker.check_validity('age', min_val=18, max_val=100)
    checker.check_consistency('cost', 'revenue', condition='col1 <= col2')
    checker.run_all_checks()


if __name__ == "__main__":
    run_all_exercises()


# ============================================================================
# EXERCÍCIOS ADICIONAIS (DESAFIOS)
# ============================================================================

"""
DESAFIO 1: Implementar um data loader que:
- Lê múltiplos CSVs de um diretório
- Valida schema de cada arquivo
- Combina em um único DataFrame
- Salva em formato Parquet particionado

DESAFIO 2: Criar um decorator @timeit que:
- Mede tempo de execução de funções
- Loga no formato JSON
- Salva métricas em um arquivo

DESAFIO 3: Implementar deduplicação fuzzy:
- Use Levenshtein distance
- Identifique registros similares
- Marque duplicatas prováveis

DESAFIO 4: Pipeline de dados com retry e exponential backoff:
- Implemente retry logic robusto
- Adicione circuit breaker pattern
- Log detalhado de erros

DESAFIO 5: Implementar caching layer:
- Cache em memória com LRU
- Cache em Redis
- TTL configurável
"""
