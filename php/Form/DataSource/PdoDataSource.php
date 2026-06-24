<?php

declare(strict_types=1);

namespace bbsengine6\Form\DataSource;

class PdoDataSource extends ArrayDataSource
{
    private array $allRows = [];

    public function __construct(\PDO $pdo, string $sql, array $params = [])
    {
        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);
        
        $rows = $stmt->fetchAll();
        
        if (count($rows) > 0) {
            $this->data = $rows[0];
            $this->allRows = $rows;
        } else {
            $this->data = [];
            $this->allRows = [];
        }
    }

    public function getAllRows(): array
    {
        return $this->allRows;
    }

    public function getRowCount(): int
    {
        return count($this->allRows);
    }
}
