## MySQL 트랜잭션 격리 수준

핵심 개념: 4가지 격리 수준, Dirty Read, Non-Repeatable Read, Phantom Read, REPEATABLE READ 기본값, MVCC

- 4가지 격리 수준: READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE. 뒤로 갈수록 동시에 실행되는 트랜잭션끼리 서로의 변경을 덜 보게 되어 정합성은 높아지고, 동시 처리 성능은 낮아진다.
- Dirty Read: 다른 트랜잭션이 아직 커밋하지 않은 변경을 읽는 현상. READ UNCOMMITTED에서 생긴다. 그 트랜잭션이 롤백되면 존재하지 않는 데이터를 읽은 셈이 된다.
- Non-Repeatable Read: 한 트랜잭션 안에서 같은 행을 두 번 읽었는데, 그 사이 다른 트랜잭션이 수정하고 커밋해서 값이 달라지는 현상. READ COMMITTED 이하에서 생긴다.
- Phantom Read: 한 트랜잭션 안에서 같은 조건으로 범위를 두 번 조회했는데, 그 사이 다른 트랜잭션이 행을 추가하거나 삭제해서 결과 행이 달라지는 현상.
- REPEATABLE READ 기본값: MySQL(InnoDB)의 기본 격리 수준은 REPEATABLE READ다. Oracle, PostgreSQL의 기본값인 READ COMMITTED와 다르다.
- MVCC: InnoDB는 변경 전 데이터를 undo 로그에 남겨 두고, 읽기 시점의 스냅샷으로 일관된 읽기(consistent read)를 한다. 그래서 일반 SELECT는 잠금 없이 읽고 쓰기와 서로 막지 않는다. REPEATABLE READ는 트랜잭션의 첫 번째 읽기 시점 스냅샷을 끝까지 쓰고, READ COMMITTED는 읽을 때마다 새 스냅샷을 쓴다.

흔한 오해:
- "REPEATABLE READ에서는 Phantom Read가 반드시 생긴다" → 표준 정의로는 생길 수 있지만, InnoDB는 일반 SELECT는 MVCC 스냅샷으로, 잠금 읽기(`SELECT ... FOR UPDATE`)는 넥스트 키 락으로 대부분 막는다. 다만 일반 SELECT와 잠금 읽기를 섞으면 잠금 읽기는 최신 커밋 데이터를 읽어 결과가 다르게 보일 수 있다.
- "격리 수준을 높이면 갱신 손실(Lost Update)도 막힌다" → REPEATABLE READ에서도 두 트랜잭션이 같은 값을 읽고 각자 계산해 덮어쓰면 한쪽 변경이 사라질 수 있다. `SELECT ... FOR UPDATE`나 낙관적 락(버전 컬럼)으로 막는다.
- "SERIALIZABLE이 가장 안전하니 쓰면 된다" → InnoDB의 SERIALIZABLE은 일반 SELECT도 공유 잠금 읽기로 바꿔 동시 처리 성능이 크게 떨어지고 잠금 대기가 늘어난다.

심화 포인트:
- 갭 락과 넥스트 키 락: REPEATABLE READ에서 잠금 읽기와 쓰기는 인덱스 레코드 사이의 간격까지 잠가 새 행 삽입을 막는다. 대신 잠금 범위가 넓어 데드락이 늘 수 있다.
- 잠금 범위를 줄이려고 READ COMMITTED로 바꾸는 서비스도 있다. 이 경우 갭 락이 대부분 사라진다.
- Spring에서는 `@Transactional(isolation = Isolation.READ_COMMITTED)`처럼 트랜잭션마다 격리 수준을 지정할 수 있다.
