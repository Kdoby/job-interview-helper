## JPA N+1 문제

핵심 개념: 지연 로딩과 추가 쿼리, fetch join, @EntityGraph, batch size, 즉시 로딩의 한계

- 지연 로딩과 추가 쿼리: 목록을 조회하는 쿼리 1번으로 엔티티 N개를 가져온 뒤, 각 엔티티의 연관 엔티티(프록시)에 접근할 때마다 조회 쿼리가 1번씩 더 나가서 총 1 + N번의 쿼리가 실행된다. 원인은 연관 엔티티를 한 번에 가져오지 않고 엔티티마다 따로 조회하는 데 있다.
- fetch join: JPQL에서 `join fetch`로 연관 엔티티를 SQL 조인 한 번에 함께 조회해 영속성 컨텍스트에 올린다. 예: `select p from Post p join fetch p.comments`. 가장 직접적인 해결 방법이다.
- @EntityGraph: Spring Data JPA 리포지토리 메서드에 `@EntityGraph(attributePaths = {"comments"})`를 붙여 JPQL을 직접 쓰지 않고도 연관 엔티티를 함께 조회한다. 내부적으로 left outer join을 쓴다.
- batch size: `@BatchSize(size = 100)` 또는 `hibernate.default_batch_fetch_size` 설정으로, 지연 로딩할 연관 엔티티를 IN 절로 묶어 한 번에 조회한다. 쿼리 수가 1 + N에서 1 + ⌈N / size⌉로 줄어든다. 페이징과 함께 쓸 수 있다.
- 즉시 로딩의 한계: 즉시 로딩(`FetchType.EAGER`)으로 바꿔도 해결되지 않는다. JPQL은 페치 전략을 보지 않고 먼저 SQL로 번역해 실행한 뒤, 즉시 로딩 설정을 보고 연관 엔티티를 엔티티마다 따로 조회하므로 N+1이 조회 시점에 바로 일어난다. 또한 어떤 쿼리가 나갈지 예측하기 어려워진다.

흔한 오해:
- "즉시 로딩(EAGER)으로 바꾸면 해결된다" → JPQL로 조회하면 N+1이 그대로, 오히려 바로 일어난다.
- "지연 로딩이 N+1의 원인이므로 지연 로딩을 쓰면 안 된다" → 지연 로딩은 추가 쿼리가 나가는 시점을 늦출 뿐이다. 실무에서는 모든 연관관계를 지연 로딩으로 두고, 필요한 곳에서 fetch join이나 batch size로 함께 조회한다.
- "N+1은 fetch join으로만 해결된다" → @EntityGraph, batch size, DTO 직접 조회로도 해결할 수 있고, 페이징이 필요하면 batch size가 더 알맞다.
- "fetch join을 쓰면 페이징도 문제없다" → 컬렉션(일대다) fetch join에 페이징을 걸면 DB가 아니라 메모리에서 페이징한다(아래 심화 포인트).

심화 포인트:
- 컬렉션 fetch join + 페이징: 조인으로 행이 늘어나 DB에서 페이징할 수 없으므로, Hibernate가 전체 결과를 메모리에 올린 뒤 페이징하고 경고 로그를 남긴다. 데이터가 많으면 메모리가 부족해질 수 있다. 다대일·일대일 연관만 fetch join하고, 컬렉션은 batch size로 조회하는 방식이 일반적이다.
- 둘 이상의 컬렉션(`List`)을 한 번에 fetch join하면 `MultipleBagFetchException`이 난다.
- 컬렉션 fetch join은 부모 엔티티가 중복된 결과를 만든다. Hibernate 6부터는 중복 엔티티를 자동으로 제거하고, Hibernate 5 이하에서는 `distinct`가 필요했다.
- DTO 직접 조회(`select new ...`)는 필요한 컬럼만 가져오지만, 조회 결과가 영속성 컨텍스트에서 관리되지 않는다.
- 해결 여부는 SQL 로그(`spring.jpa.show-sql`, p6spy 등)에서 실제로 나간 쿼리 수로 확인한다.
