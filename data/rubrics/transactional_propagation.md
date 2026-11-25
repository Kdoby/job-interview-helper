## @Transactional 전파 속성

핵심 개념: 물리·논리 트랜잭션, REQUIRED, REQUIRES_NEW, NESTED와 savepoint, rollback-only, 내부 호출 시 미적용

- 물리·논리 트랜잭션: 물리 트랜잭션은 실제 DB 커넥션에서 시작하고 커밋하는 트랜잭션이고, 논리 트랜잭션은 트랜잭션 매니저가 `@Transactional` 메서드 단위로 다루는 트랜잭션이다. 이미 진행 중인 트랜잭션에 참여하면 여러 논리 트랜잭션이 하나의 물리 트랜잭션을 공유한다. 모든 논리 트랜잭션이 커밋되어야 물리 트랜잭션이 커밋되고, 실제 커밋은 처음 시작한 트랜잭션이 끝날 때 한 번 일어난다.
- REQUIRED: 기본값. 진행 중인 트랜잭션이 있으면 참여하고, 없으면 새로 시작한다.
- REQUIRES_NEW: 항상 새 물리 트랜잭션을 시작하고, 기존 트랜잭션은 잠시 보류(suspend)한다. 내부가 롤백되어도 외부에 영향이 없다(예외를 외부로 던지지 않는 경우). 커넥션을 동시에 두 개 쓰므로 커넥션 풀이 부족해질 수 있다.
- NESTED와 savepoint: 기존 트랜잭션 안에 savepoint를 만들어 중첩 트랜잭션을 시작한다. 내부가 롤백되면 savepoint까지만 되돌리고, 외부가 롤백되면 내부도 함께 롤백된다. JDBC savepoint를 쓰므로 JPA(`JpaTransactionManager`)에서는 기본으로 지원되지 않는다.
- rollback-only: 참여한 내부 트랜잭션에서 런타임 예외가 나 롤백 대상이 되면, 공유하는 물리 트랜잭션에 rollback-only 표시가 붙는다. 외부에서 그 예외를 catch하고 커밋해도 `UnexpectedRollbackException`이 나며 전체가 롤백된다.
- 내부 호출 시 미적용: `@Transactional`은 프록시(AOP)로 동작하므로, 같은 클래스 안에서 `this.method()`로 호출하면 프록시를 거치지 않아 트랜잭션과 전파 속성이 적용되지 않는다. 별도 빈으로 분리해서 해결한다.

흔한 오해:
- "내부 트랜잭션의 예외를 외부에서 catch하면 외부는 정상 커밋된다" → REQUIRED로 참여했다면 rollback-only 때문에 `UnexpectedRollbackException`이 나고 전체가 롤백된다. 독립시켜야 하면 REQUIRES_NEW를 쓴다.
- "REQUIRES_NEW로 하면 내부 예외가 외부에 아무 영향도 없다" → 트랜잭션은 분리되지만, 예외를 외부로 던지면 외부 트랜잭션도 그 예외로 롤백된다. 외부에서 예외를 처리해야 한다.
- "같은 클래스의 메서드에 `REQUIRES_NEW`를 붙이면 새 트랜잭션이 열린다" → 내부 호출이면 프록시를 거치지 않아 적용되지 않는다.

심화 포인트:
- 나머지 전파 속성: `SUPPORTS`(있으면 참여, 없으면 트랜잭션 없이), `MANDATORY`(없으면 예외), `NOT_SUPPORTED`(트랜잭션 없이 실행, 기존 것은 보류), `NEVER`(있으면 예외).
- 롤백 규칙: 기본으로 런타임 예외(`RuntimeException`)와 `Error`만 롤백하고, 체크 예외는 커밋한다. `rollbackFor`로 바꿀 수 있다.
- `private` 메서드나 `final` 메서드에는 프록시가 적용되지 않으므로 `@Transactional`이 동작하지 않는다.
- 로그 기록처럼 본 작업이 실패해도 남겨야 하는 일에 REQUIRES_NEW를 쓰는 것이 대표적인 사용 예다.
