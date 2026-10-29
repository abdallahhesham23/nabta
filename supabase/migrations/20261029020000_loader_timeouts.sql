-- A dropped client connection once left a publish stuck mid-COPY for minutes, holding its locks.
-- Cap the loader's statements so such a session rolls itself back.
alter role nabta_loader set statement_timeout = '5min';
alter role nabta_loader set idle_in_transaction_session_timeout = '2min';
