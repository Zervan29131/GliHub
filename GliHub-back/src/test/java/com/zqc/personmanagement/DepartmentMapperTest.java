package com.zqc.personmanagement;

import com.zqc.personmanagement.mapper.DepartmentMapper;
import com.zqc.personmanagement.pojo.Department;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;

@SpringBootTest
public class DepartmentMapperTest {
    @Autowired
    private DepartmentMapper departmentMapper;

    /**
     * department测试
     */

    @Test
    void testQueryDepartmentList() {
        List<Department> departments = departmentMapper.queryDepartmentList();
        for (Department department : departments) {
            System.out.println(department);
        }
    }

    @Test
    void testQueryDepartmentById() {
        Department department = departmentMapper.queryDepartmentById(101);
        System.out.println(department);
    }

    @Test
    void testAddDepartment() {
        int x = departmentMapper.addDepartment(new Department(111, "部门x"));
        System.out.println(x);
    }

    @Test
    void testUpdateDepartment() {
        int y = departmentMapper.updateDepartment(new Department(111, "部门y"));
        System.out.println(y);
    }

    @Test
    void testDeleteDepartmentById() {
        int i = departmentMapper.deleteDepartmentById(111);
        System.out.println(i);
    }
}
