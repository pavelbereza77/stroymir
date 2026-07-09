#!/bin/bash
set -eux

# Создаём ядро с минимальной конфигурацией
echo "Creating core..."
solr create -c oscar_stroymir -n basic

# Ждём, пока Solr загрузит ядро (~10 секунд)
echo "Waiting for Solr to initialize..."
sleep 10

# Перезагружаем ядро с новой схемой
echo "Reloading core..."
curl "http://localhost:8983/solr/admin/cores?action=RELOAD&core=oscar_stroymir"