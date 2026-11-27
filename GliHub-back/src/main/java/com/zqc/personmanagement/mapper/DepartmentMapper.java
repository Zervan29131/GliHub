package com.zqc.personmanagement.mapper;

import com.zqc.personmanagement.pojo.Department;
import org.apache.ibatis.annotations.Mapper;
import org.springframework.stereotype.Repository;

import java.util.List;

// 注解表示了这是一个mybatis的mapper类
@Mapper
@Repository
public interface DepartmentMapper {
    List<Department> queryDepartmentList();
    Department queryDepartmentById(int id);
    int addDepartment(Department department);
    int updateDepartment(Department department);
    int deleteDepartmentById(int id);
}
