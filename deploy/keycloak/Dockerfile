ARG KEYCLOAK_IMAGE
FROM ${KEYCLOAK_IMAGE} AS builder
ENV KC_DB=postgres KC_HEALTH_ENABLED=true
RUN /opt/keycloak/bin/kc.sh build

FROM ${KEYCLOAK_IMAGE}
COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY --chown=keycloak:keycloak --chmod=0755 entrypoint.sh /opt/keycloak/bin/bridge-entrypoint.sh
COPY --chown=keycloak:keycloak --chmod=0755 healthcheck.sh /opt/keycloak/bin/bridge-healthcheck.sh
COPY --chown=keycloak:keycloak nextcloud-realm.json /opt/keycloak/data/import/nextcloud-realm.json
ENTRYPOINT ["/opt/keycloak/bin/bridge-entrypoint.sh"]
